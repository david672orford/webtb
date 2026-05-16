"""Encode WAV files in MP3 and OGG-Vorbis for the <audio> tag"""
#
#   <audio>
#	 <source src="file.mp3" type="audio/mpeg">
#	 <source src="file.ogg" type="audio/ogg">
#   </audio>
#

#set -e -u
#
#if [ "$1" != "-o" ]
#	then
#	echo "Usage: $0 -o <outdir> <recording>..."
#	exit 1
#	fi
#shift
#
#targetdir="$1"
#shift
#
#for filename in "$@"
#	do
#	basename=`basename "$filename"`
#	basename=`echo "$basename" | sed -e 's/\.[^\.]*$//'`
#	echo "$basename"
#
#	# MP3
#	ffmpeg \
#		-i "$filename" \
#		-c libmp3lame \
#		-b:a 64k \
#		"${targetdir}/${basename}.mp3"
#
#	# Ogg Vorbis
#	ffmpeg \
#		-i "$filename" \
#		-c libvorbis \
#		-b:a 64k \
#		"${targetdir}/${basename}.ogg"
#
#	done

import argparse
import os
import wave
from subprocess import run

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("-o", "--outdir", default=".", help="Output directory")
	parser.add_argument("filenames", nargs="+", help="Source audio files to process")
	opts = parser.parse_args(args=argv)

	os.makedirs(opts.outdir, exist_ok=True)

	for filename in opts.filenames:
		base_name = os.path.splitext(os.path.basename(filename))[0]
		if opts.verbose:
			size = os.path.getsize(filename)
			with wave.open(filename, "rb") as fh:
				duration = fh.getnframes() / fh.getframerate()
			print(f"Encoding {filename} ({size} bytes, {duration:.1f} seconds)")

		# Base ffmpeg flags common to both runs
		ffmpeg_base = [
			"ffmpeg",
			"-hide_banner",
			"-loglevel", "error",
			"-ch_layout", "mono",
			"-i", filename,
			"-y",
			]

		# MP3
		mp3 = os.path.join(opts.outdir, f"{base_name}.mp3")
		if opts.verbose:
			print(f" → {mp3}", end="", flush=True)
		run(ffmpeg_base + ["-c:a", "libmp3lame", "-b:a", "64k", mp3], check=True)
		size = os.path.getsize(mp3)
		if opts.verbose:
			print(f" ({size} bytes)")

		# Ogg Vorbis
		ogg = os.path.join(opts.outdir, f"{base_name}.ogg")
		if opts.verbose:
			print(f" → {ogg}", end="", flush=True)
		run(ffmpeg_base + ["-c:a", "libvorbis", "-b:a", "64k", ogg], check=True)
		size = os.path.getsize(mp3)
		if opts.verbose:
			print(f" ({size} bytes)")

		if opts.verbose:
			print()

	return 0
