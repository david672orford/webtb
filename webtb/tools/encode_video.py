"""Convert videos to streamable formats"""
# Required software:
# * FFmpeg (apt install ffmpeg)
# * MP4Box (apt install gpac)
#
# Compiling FFmpeg:
# $ sudo apt-get install nasm libx264-dev libfdk-aac-dev libmp3lame-dev libopus-dev libvpx-dev
# $ ./configure --enable-gpl --enable-libx264 --enable-libmp3lame --enable-nonfree --enable-libfdk-aac --enable-libopus --enable-libvpx
# $ make
# $ sudo make install
#
# Lossless format for exporting from Openshot:
#  huffyuv for video
#  pcm_s16le for audio
#  avi container
#
# References:
# * General
#   * https://www.brightcove.com/en/blog/2013/09/what-formats-do-i-need-for-html5-video
#   * https://www.iandevlin.com/blog/2012/08/html5/responsive-html5-video
#   * https://trac.ffmpeg.org/wiki/Encode/HighQualityAudio
#   * http://stackoverflow.com/questions/7451635/how-to-detect-supported-video-formats-for-the-html5-video-tag
#   * https://developer.mozilla.org/en-US/docs/Web/Media/Formats/Video_codecs
#   * https://videoblerg.wordpress.com/2017/11/10/ffmpeg-and-how-to-use-it-wrong/ (TODO: review this)
# * H.264 and HLS
#   * https://github.com/dailymotion/hls.js/
#   * https://trac.ffmpeg.org/wiki/Encode/H.264
#   * https://zencoder.com/en/hls-guide
#   * https://developer.apple.com/library/content/referencelibrary/GettingStarted/AboutHTTPLiveStreaming/about/about.html
#   * https://developer.apple.com/library/content/documentation/NetworkingInternet/Conceptual/StreamingMediaGuide/FrequentlyAskedQuestions/FrequentlyAskedQuestions.html
#   * https://videoblerg.wordpress.com/2015/12/16/intelligent-video-encoding/
#   * https://trac.ffmpeg.org/wiki/Encode/AAC
#   * http://www.streamingmedia.com/Articles/Editorial/Featured-Articles/How-to-Produce-High-Quality-H.264-Video-Files-94216.aspx
#   * https://developer.apple.com/library/content/technotes/tn2224/_index.html (HLS Recomendations)
#   * http://superuser.com/questions/908280/what-is-the-correct-way-to-fix-keyframes-in-ffmpeg-for-dash
# * VP9 and DASH
#   * https://github.com/google/shaka-player
#   * https://trac.ffmpeg.org/wiki/Encode/VP9
#   * http://wiki.webmproject.org/ffmpeg/vp9-encoding-guide
#   * https://sites.google.com/a/webmproject.org/wiki/ffmpeg/vp9-encoding-guide (mirror of above?)
#   * http://wiki.webmproject.org/adaptive-streaming/instructions-to-playback-adaptive-webm-using-dash
#   * http://rigor.com/blog/2016/02/optimizing-webm-video-for-faster-streaming-and-seeking
#   * https://developer.mozilla.org/ru/docs/Web/HTML/DASH_Adaptive_Streaming_for_HTML_5_Video
#
# HTML <video> codecs attributes values for video/mp4:
#  avc1.42E0xx: H.264 baseline where xx is the AVC level multiplied by 10
#   avc1.42E01E: H.264 Baseline Profile Level 3.0
#   avc1.42E01F: H.264 Baseline Profile Level 3.1
#  avc1.4D40xx: H.264 Main where xx is the AVC level multiplied by 10
#   avc1.4D401E: H.264 Main Profile Level 3
#  avc1.6400xx: H.264 High where xx is the AVC level multiplied by 10
#   avc1.640029: H.264 High Profile Level 4.1
#
# HTML <video> codecs attribute values for audio/mp4:
#  mp4a.40.2: AAC-LC
#  mp4a.40.5: HE-AAC
#

import argparse
import sys
import os
import subprocess
import json
import re
import urllib.parse
import shlex
import glob
from typing import cast

#=========================================================================
# Utility
#=========================================================================

class VideoInfo:
	def __init__(self, video_filename:str):
		args = cast(list[str], "ffprobe -v quiet -print_format json -show_format -show_streams".split(" "))
		args.append(video_filename)
		self.ffprobe = json.loads(subprocess.check_output(args).decode("utf-8"))
		self.video_stream = self.ffprobe["streams"][0]
		assert self.video_stream["codec_type"] == "video"

	def get_dimensions(self):
		return (self.video_stream["width"], self.video_stream["height"])

	def get_bpp(self, frame_rate):
		if "bit_rate" in self.video_stream:
			bit_rate = self.video_stream["bit_rate"]
		elif len(self.ffprobe["streams"]) == 1:		# no audio
			bit_rate = self.ffprobe["format"]["bit_rate"]
		else:
			assert False, "bit_rate missing"
		return (float(bit_rate) / (self.video_stream["width"] * self.video_stream["height"]) / frame_rate)

	def get_duration(self):
		return float(self.ffprobe["format"]["duration"])

	def get_frame_rate(self):
		frame_rate = self.video_stream["r_frame_rate"]
		if frame_rate == "24/1":
			return 24
		if frame_rate == "24000/1001":
			return 24
		elif frame_rate == "30/1":
			return 30
		elif frame_rate == "30000/1001":
			return 30
		else:
			assert False, frame_rate

	def get_aspect_ratio(self):
		return self.video_stream['display_aspect_ratio']

def run(argv, silent=False):
	if not silent:
		print("========================================================")
		print(" ".join(map(shlex.quote, argv)))
	subprocess.check_call(argv)

#=========================================================================
# H264 video and AAC audio which are suitable
# for HTTP streaming or for downloading.
#=========================================================================

def render_h264(video_filename:str, video_info:VideoInfo, output_stem:str, crop, aspect_ratio, verbose:bool):
	frame_rate = video_info.get_frame_rate()

	if aspect_ratio == "16:9":
		resolutions = (							# These resolutions are from Youtube
			(256,144, 25, 16000, False),
			(426,240, 25, 32000, False),
			(640,360, 23, 32000, True),			# 1/2 of Full HD
			(854,480, 23, 48000, False),
			(1280,720, 23, 64000, True),		# HD
			(1920,1080, 23, 128000, True),		# Full HD
			)
	else:										# 4:3 or cropped to 4:3
		resolutions = (
			(160,120, 25, 16000, False),		# 1/4 of VGA NTSC
			(320,240, 25, 32000, True),			# 1/2 of VGA NTSC
			(480,360, 23, 32000, False),		# 3/4 of VGA NTSC
			(640,480, 23, 48000, True),			# VGA NTSC
			(960,720, 23, 64000, True),			# cropped HD
			(1440,1080, 23, 128000, True),		# cropped Full HD
			)

	# Duration of each HLS segment in seconds
	HLS_SEGMENT_SIZE=6

	H264_VIDEO_OPTS="""
		-c:v libx264
		-profile:v high -level 4.1 -preset slow
		-pix_fmt yuv420p
		-r {FRAME_RATE}
		-aspect {ASPECT}
		-x264opts keyint={IFRAME_INTERVAL}:min-keyint={IFRAME_INTERVAL}:scenecut=-1
		""".format(
				FRAME_RATE=frame_rate,
				IFRAME_INTERVAL=(HLS_SEGMENT_SIZE * frame_rate),
				ASPECT=aspect_ratio
				).split()
	H264_CODEC_ATTRIBUTE="avc1.640029"

	# This AAC-LC encoder is available in FFmpeg binaries in Ubuntu.
	#AAC_AUDIO_OPTS="-strict experimental -c:a aac -ar 48000".split()
	AAC_AUDIO_OPTS="-c:a aac -ar 48000".split()
	AAC_CODEC_ATTRIBUTE="mp4a.40.2"

	# To use this AAC-HE encoder (AAC-HE works better at low bitrates),
	# you have to build FFmpeg from source.
	#AAC_AUDIO_OPTS="-c:a libfdk_aac -profile:a aac_he -ar 48000".split()
	#AAC_CODEC_ATTRIBUTE="mp4a.40.5"

	if not os.path.isdir(output_stem):
		os.mkdir(output_stem)

	hls_output_filenames = []
	for width, height, crf, audio_bitrate, downloadable in resolutions:

		# Skip resolutions which are larger than the source material
		if height > crop[1]:
			continue

		if verbose:
			print("========================================================")
			print("= H264 %dx%d" % (width, height))
			print("========================================================")

		# Pass 1--Figure out how complex this video is
		test_filename = "%s %dx%d.test.mp4" % (output_stem, width, height)
		argv = [
			"ffmpeg",
			"-hide_banner"
			]
		argv.extend(("-i", video_filename))
		argv.extend(("-filter:v", "crop=%d:%d:%d:%d,scale=%dx%d" % (*crop, width, height)))
		argv.extend(H264_VIDEO_OPTS)
		argv.extend(("-crf", str(crf)))
		argv.append("-an")
		argv.extend("-f mp4 -y".split())
		argv.append(test_filename)
		run(argv)

		bpp = VideoInfo(test_filename).get_bpp(frame_rate)
		os.remove(test_filename)
		video_bitrate = int(width * height * frame_rate * bpp)
		print("resolution=%dx%d, bpp=%.2f, video_bitrate=%s" % (width, height, bpp, video_bitrate))
		mp4_output_filename = "%s %dx%d.mp4" % (output_stem, width, height)
		hls_output_filename = "%s/%dx%d-%dk.m3u8" % (output_stem, width, height, (video_bitrate + audio_bitrate) / 1000)

		# Pass 2--First ABR pass
		argv = [
			"ffmpeg",
			"-hide_banner"
			]
		argv.extend(("-i", video_filename))
		argv.extend(("-filter:v", "crop=%d:%d:%d:%d,scale=%dx%d" % (*crop, width, height)))
		argv.extend(H264_VIDEO_OPTS)
		argv.extend(("-b:v", "%dk" % (video_bitrate / 1000)))
		argv.extend(AAC_AUDIO_OPTS)
		argv.extend(("-b:a", "%dk" % (audio_bitrate / 1000)))
		argv.extend("-pass 1".split())
		argv.extend("-f mp4 -y /dev/null".split())
		run(argv)

		# Pass 3--Second ABR pass
		argv = [
			"ffmpeg",
			"-hide_banner"
			]
		argv.extend(("-i", video_filename))
		argv.extend(("-filter:v", "crop=%d:%d:%d:%d,scale=%dx%d" % (*crop, width, height)))
		argv.extend(H264_VIDEO_OPTS)
		argv.extend(("-b:v", "%dk" % (video_bitrate / 1000)))
		argv.extend(AAC_AUDIO_OPTS)
		argv.extend(("-b:a", "%dk" % (audio_bitrate / 1000)))
		argv.extend("-pass 2".split())
		argv.extend("-f mp4 -y".split())
		argv.append(mp4_output_filename)
		run(argv)

		# Reinterleave the MP4 file since it is sometimes used for "pseudo streaming".
		run("MP4Box -inter 500".split() + [mp4_output_filename])

		# Pass 4--Remux for HLS
		argv = [
			"ffmpeg",
			"-hide_banner"
			]
		argv.extend(("-i", mp4_output_filename))
		argv.extend("-c:v copy -c:a copy".split())
		argv.extend("-movflags +faststart".split())
		argv.extend("-hls_time {HLS_SEGMENT_SIZE} -hls_list_size 0 -hls_flags single_file -f hls -y".format(HLS_SEGMENT_SIZE=HLS_SEGMENT_SIZE).split())
		argv.append(hls_output_filename)
		run(argv)
		hls_output_filenames.append((width, height, (video_bitrate + audio_bitrate), hls_output_filename))

		if not downloadable:
			os.remove(mp4_output_filename)

	m3u8 = open("%s.m3u8" % output_stem, "w")
	m3u8.write("#EXTM3U\n")
	for width, height, bitrate, output_filename in hls_output_filenames:
		m3u8.write("#EXT-X-STREAM-INF:BANDWIDTH={BANDWIDTH},RESOLUTION={WIDTH}x{HEIGHT},CODECS=\"{CODECS}\"\n".format(
			BANDWIDTH=bitrate,
			WIDTH=width,
			HEIGHT=height,
			CODECS=",".join((H264_CODEC_ATTRIBUTE, AAC_CODEC_ATTRIBUTE)),
			))
		url = urllib.parse.quote("%s/%s" % (os.path.basename(output_stem), os.path.basename(output_filename)))
		m3u8.write("%s\n" % url)
	m3u8.close()

	for filename in glob.glob("ffmpeg2pass*"):
		os.remove(filename)

#=========================================================================
# VP9
#=========================================================================

def render_vp9(video_filename:str, video_info:VideoInfo, output_stem:str, crop, aspect_ratio, verbose:bool):
	frame_rate = video_info.get_frame_rate()

	if aspect_ratio == "16:9":
		resolutions = (							# These resolutions are from Youtube
			(256,144, 36, 16000, False),
			(426,240, 36, 32000, False),
			(640,360, 34, 32000, True),
			(854,480, 34, 48000, False),
			(1280,720, 34, 64000, True),		# HD
			(1920,1080, 34, 128000, True),		# Full HD
			)
	else:										# 4:3 or cropped to 4:3
		resolutions = (
			(160,120, 36, 16000, False),		# 1/4 of VGA NTSC
			(320,240, 36, 32000, True),			# 1/2 of VGA NTSC
			(480,360, 34, 32000, False),		# 3/4 of VGA NTSC
			(640,480, 34, 48000, True),			# VGA NTSC
			(960,720, 34, 64000, True),			# Cropped HD
			(1440,1080, 34, 128000, True),		# Cropped Full HD
			)

	# Options used on all passes
	# According to <http://wiki.webmproject.org/ffmpeg/vp9-encoding-guide>
	# "Multi-threaded encoding may be used if -threads > 1 and -tile-columns > 0."
	# According to <https://trac.ffmpeg.org/wiki/Encode/VP9>
	# Starting with libvpx 1.7.0 using "-row-mt 1" will "greatly enhance the
	# number of threads the encoder can utilize".
	WEBM_VIDEO_OPTS1="""
		-c:v libvpx-vp9
		-pix_fmt yuv420p
		-r {FRAME_RATE}
		-aspect {ASPECT}
		-keyint_min 150 -g 150
		-tile-columns 6 -frame-parallel 1
		-threads 4 -row-mt 1
		""".format(
			FRAME_RATE=frame_rate,
			ASPECT=aspect_ratio
			).split()

	# Extra options for final pass
	# According to <http://wiki.webmproject.org/ffmpeg/vp9-encoding-guide>
	# -auto-alt-ref and -lag-in-frames "turn on VP9's alt-ref frames, a VP9
	# feature that enhances quality".
	# For explanation of "-anrn-maxframes -1" see https://htrd.su/wiki/zhurnal/2015/11/06/ffmpeg_i_vp9_libvpx
	WEBM_VIDEO_OPTS2="""
		-auto-alt-ref 1 -lag-in-frames 25
		-arnr-maxframes -1
		""".split()

	WEBM_AUDIO_OPTS="-c:a libopus -ar 48000".split()

	DASH_AUDIO_BITRATES = (24000, 64000)

	duration_hours = video_info.get_duration() / 3600
	reserve_index_space = int(16000 * duration_hours)

	if not os.path.isdir(output_stem):
		os.mkdir(output_stem)

	dash_output_filenames = []
	for width, height, crf, audio_bitrate, downloadable in resolutions:

		# Skip resolutions which are larger than the source material
		if height > crop[1]:
			continue

		if verbose:
			print("========================================================")
			print("= Webm %dx%d" % (width, height))
			print("========================================================")

		# Pass 1--Figure out how complex this video is
		test_filename = "%s %dx%d.test.webm" % (output_stem, width, height)
		argv = ["ffmpeg", "-hide_banner"]
		argv.extend(("-i", video_filename))
		argv.extend(("-filter:v", "crop=%d:%d:%d:%d,scale=%dx%d" % (*crop, width, height)))
		argv.extend(WEBM_VIDEO_OPTS1)
		argv.extend("-speed 4".split())
		argv.extend(("-crf", str(crf), "-b:v", "0"))
		argv.append("-an")
		argv.extend("-f webm -y".split())
		argv.append(test_filename)
		run(argv)

		bpp = VideoInfo(test_filename).get_bpp(frame_rate)
		os.remove(test_filename)
		video_bitrate = int(width * height * frame_rate * bpp)
		print("resolution=%dx%d, bpp=%.2f, video_bitrate=%s" % (width, height, bpp, video_bitrate))
		output_filename = "%s %dx%d.webm" % (output_stem, width, height)
		dash_output_filename = "%s/video-%dx%d-%dk.webm" % (output_stem, width, height, (video_bitrate + audio_bitrate) / 1000)

		# Pass 2--First ABR pass
		argv = ["ffmpeg", "-hide_banner"]
		argv.extend(("-i", video_filename))
		argv.extend(("-filter:v", "crop=%d:%d:%d:%d,scale=%dx%d" % (*crop, width, height)))
		argv.extend(WEBM_VIDEO_OPTS1)
		argv.extend("-pass 1 -speed 4".split())
		argv.extend(("-b:v", "%dk" % video_bitrate))
		argv.append("-an")
		argv.extend("-f webm -y /dev/null".split())
		run(argv)

		# Pass 3--Second ABR pass
		argv = ["ffmpeg", "-hide_banner"]
		argv.extend(("-i", video_filename))
		argv.extend(("-filter:v", "crop=%d:%d:%d:%d,scale=%dx%d" % (*crop, width, height)))
		argv.extend(WEBM_VIDEO_OPTS1)
		argv.extend(WEBM_VIDEO_OPTS2)
		argv.extend("-pass 2 -speed 1".split())
		argv.extend(("-b:v", "%dk" % (video_bitrate / 1000)))
		argv.extend(WEBM_AUDIO_OPTS)
		argv.extend(("-b:a", "%dk" % (audio_bitrate / 1000)))
		argv.extend(("-reserve_index_space", str(reserve_index_space)))
		argv.extend("-f webm -y".split())
		argv.append(output_filename)
		run(argv)

		# Pass 4--Remux for DASH
		argv = ["ffmpeg", "-hide_banner"]
		argv.extend(("-i", output_filename))
		argv.extend("-c:v copy".split())
		argv.append("-an")
		argv.extend("-dash 1 -f webm -y".split())
		argv.append(dash_output_filename)
		run(argv)
		dash_output_filenames.append(dash_output_filename)

		if not downloadable:
			os.remove(output_filename)

	video_variants_count = len(dash_output_filenames)

	# Encode audio for DASH
	for audio_bitrate in DASH_AUDIO_BITRATES:
		output_filename = "%s/audio-%dk.webm" % (output_stem, (audio_bitrate / 1000))
		argv = ["ffmpeg", "-hide_banner"]
		argv.extend(("-i", video_filename))
		argv.append("-vn")
		argv.extend(("-c:a", "libopus"))
		argv.extend(("-b:a", "%dk" % (audio_bitrate / 1000)))
		argv.extend("-f webm -y -dash 1".split())
		argv.append(output_filename)
		run(argv)
		dash_output_filenames.append(output_filename)

	# Create DASH manifest
	argv = ["ffmpeg", "-hide_banner"]
	for output_filename in dash_output_filenames:
		argv.extend(("-f", "webm_dash_manifest", "-i", output_filename))
	argv.extend(("-c", "copy"))
	for i in range(video_variants_count+len(DASH_AUDIO_BITRATES)):
		argv.extend(("-map", str(i)))
	argv.extend(("-f", "webm_dash_manifest"))
	#argv.extend(("-adaptation_sets", "id=0,streams=0,1,2 id=1,streams=3"))
	adaptation_sets = \
		"id=0,streams=" + ",".join(map(str,range(video_variants_count))) \
		+ " " \
		+ "id=1,streams=" + ",".join(map(lambda i: str(video_variants_count + i),range(len(DASH_AUDIO_BITRATES))))
	argv.extend(("-adaptation_sets", adaptation_sets))
	argv.append("%s.mpd" % output_stem)
	run(argv)

	# Correct bad paths to the media segments
	f = open("%s.mpd" % output_stem)
	text = f.read()
	f.close()
	text = text.replace("<BaseURL>", "<BaseURL>%s/" % urllib.parse.quote(os.path.basename(output_stem)))
	f = open("%s.mpd" % output_stem, "w")
	f.write(text)
	f.close()

	for filename in glob.glob("ffmpeg2pass*"):
		os.remove(filename)

#=========================================================================
# Main
#=========================================================================

def main(argv:list[str]) -> int:

	# TODO: Consider porting to argparse
	# https://docs.python.org/3/library/argparse.html
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("-o", "--outdir", default=".")
	parser.add_argument("--h264", action="store_true")
	parser.add_argument("--vp9", action="store_true")
	parser.add_argument("--crop-to-4x3", action="store_true")
	parser.add_argument("video_filenames", nargs="+")
	opts = parser.parse_args(args=argv)

	# Fail early if these programs are not available
	try:
		run(["MP4Box", "-version"], silent=True)
		run(["ffmpeg", "-version"], silent=True)
	except FileNotFoundError as e:
		print(f"Missing dependences. Please install: {e.filename}", file=sys.stderr)
		return 100

	for video_filename in opts.video_filenames:
		if not os.path.isfile(video_filename):
			print(f"No such file: {video_filename}", file=sys.stderr)
			return 5

	for video_filename in opts.video_filenames:
		if opts.verbose:
			print(f"{video_filename}")
		video_info = VideoInfo(video_filename)
		width, height = video_info.get_dimensions()
		if opts.verbose:
			print(" Video size: %dx%d" % (width, height))

		aspect_ratio = video_info.get_aspect_ratio()
		if not (aspect_ratio == "16:9" or aspect_ratio == "4:3"):
			print(f"Invalid or unacceptable aspect ratio: {aspect_ratio}", file=sys.stderr)
			return 10

		# Determine the part of the frame which we should encode
		# (width, height, x offset, y offset)
		if aspect_ratio == "16:9" and opts.crop_to_4x3:
			if (width, height) == (1920, 1080):		# Full HD
				crop = (1440, height, 240,0)
			elif (width, height) == (1280, 720):	# HD
				crop = (960, height, 160,0)
			else:
				print(f"Unsupported video resolution: {width}x{height}", file=sys.stderr)
				return 1
			aspect_ratio = "4:3"
		else:
			crop = (width, height, 0, 0)

		basename = os.path.splitext(os.path.basename(video_filename))[0]
		basename = re.sub(r"\s+\d+x\d+$", "", basename)
		output_stem = "%s/%s" % (opts.outdir, basename)

		if opts.h264:
			render_h264(video_filename, video_info, output_stem, crop, aspect_ratio, opts.verbose)
		if opts.vp9:
			render_vp9(video_filename, video_info, output_stem, crop, aspect_ratio, opts.verbose)

	return 0
