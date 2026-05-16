"""Add a Youtube video to an Xspf playlist"""
#
# Usage example:
#  xspf-youtube playlist.xspf https://www.youtube.com/watch?v=C0DPdy98e4c
#
# This script ignores everything in the URL except the "v" parameter, so any Youtube
# URL which will play the video will work including the video's Youtube page URL,
# its embedding URL, and the short sharing URL's. The generated playlist entry will
# always use the URL of the video's Youtube page.
#
# Useful references for Youtube:
# https://tyrrrz.me/blog/reverse-engineering-youtube
# https://github.com/Tyrrrz/YoutubeExplode
#

import argparse
import os
import json
import subprocess
from urllib.request import urlopen
from urllib.parse import urlparse, parse_qsl

from webtb.libs.xspf import Playlist, PlaylistItem

# Use the API for the Youtube web player to get information about a video.
# Note that this is not an official API and it sometimes changes.
class YoutubeVideoMetadata(object):
	def __init__(self, video_id):
		# Call the endpoint which the Youtube web player uses to get information about a video
		result = urlopen("https://www.youtube.com/get_video_info?el=embedded&video_id=%s" % video_id)
		assert result.getcode() == 200
		result_text = result.read()

		# The result is a URL-encoded dictionary
		metadata = dict(parse_qsl(result_text.decode("ascii")))
		#self.pretty_print("metadata", metadata)
		assert metadata["status"] == "ok", "Youtube metadata request failed: {status}: {reason}".format_map(metadata)

		# Within this dictionary is a JSON-encoded data structure which contains
		# most all the information about the video
		player_response = json.loads(metadata["player_response"])
		#self.pretty_print("player_response", player_response)

		playabilityStatus = player_response["playabilityStatus"]
		assert playabilityStatus["status"] == "OK", playabilityStatus
		assert playabilityStatus["playableInEmbed"], playabilityStatus

		# Extract the metadata which we need for the xspf playlist
		video_details = player_response["videoDetails"]
		self.title = video_details["title"]
		self.author = video_details["author"]
		self.length_seconds = int(video_details["lengthSeconds"])

	def pretty_print(self, name, value):
		print("%s: %s" % (name, json.dumps(value, indent=2, ensure_ascii=False)))

	def print(self):
		print("  Title: %s" % self.title)
		print("  Channel: %s" % self.author)
		print("  Duration: %s" % self.length_seconds)

# Extract the query parameters from a URL and return them as a dict().
def url_query(url):
	url_obj = urlparse(url)
	params = dict(parse_qsl(url_obj.query))
	return params

# Extract the video ID from a Youtube video URL. If it is a playlist URL,
# use youtube-dl to get the playlist. In either case this returns a list.
def get_video_ids(args):
	video_ids = []
	for item in args:
		if "://" in item:
			params = url_query(item)
			if "list" in params:		# If URL of Youtube playlist
				playlist = json.loads(subprocess.check_output(("youtube-dl", "--flat-playlist", "--dump-single-json", item)))
				for entry in playlist["entries"]:
					video_ids.append(entry["url"])
			elif "v" in params:
				video_ids.append(params["v"])
			else:
				raise AssertionError("Not a video or playlist URL")
		else:
			video_ids.append(item)
	return video_ids

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("--verify", action="store_true")
	parser.add_argument("playlist", help="Playlist to which to add the videos")
	parser.add_argument("urls", nargs="+", help="Youtube video URLs to add")
	opts = parser.parse_args(args=argv)

	playlist_exists = os.path.exists(opts.playlist)
	if playlist_exists:
		print("Appending to playlist %s..." % opts.playlist)
	else:
		print("Creating playlist %s..." % opts.playlist)
	playlist = Playlist(opts.playlist if playlist_exists else None)

	# For deduplication
	video_urls = set()

	# Copy the existing tracks from the source playlist.
	# If the --verify option is present, fetch the Youtube metadata of each
	# to make sure they are still on Youtube.
	for track in playlist:
		if opts.verify:
			if opts.verbose:
				print(" %s" % track.location)
				print("  Title: %s" % track.title)
				print("  Channel: %s" % track.album)
				print("  Duration: %s" % track.duration_seconds)
			metadata = YoutubeVideoMetadata(url_query(track.location)["v"])
			metadata.print()
		video_urls.add(track.location)

	# Add new videos
	changes = 0
	for video_id in get_video_ids(opts.urls):
		video_url = "https://www.youtube.com/watch?v=%s" % video_id
		if opts.verbose:
			print(" +%s" % video_url)
		if video_url in video_urls:
			if opts.verbose:
				print(" already present")
			continue
		metadata = YoutubeVideoMetadata(video_id)
		metadata.print()
		track = PlaylistItem(
			title = metadata.title,
			album = metadata.author,
			location = video_url,
			annotation = "",
			image = ("https://img.youtube.com/vi/%s/mqdefault.jpg" % video_id),
			duration_seconds = metadata.length_seconds,
			)
		playlist.append(track)
		video_urls.add(track.location)
		changes += 1

	if changes > 0:
		playlist.save(opts.playlist)

	return 0
