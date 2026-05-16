"""Convert SVG files to PNG and run PNGCrush on them"""

#set -u -e
#outdir="."
#if [ "$1" = "-o" ]
#	then
#	shift
#	outdir="$1"
#	shift
#	fi
#for svg in "$@"
#	do
#	echo "  $svg"
#	png=$outdir/`basename "$svg" .svg`.png
#	if [ ! -f "$png" -o "$svg" -nt "$png" ]
#		then
#			echo "    Generating..."
#			rsvg-convert "$svg" -o .tmp.png
#			pngcrush -q .tmp.png "$png"
#			rm .tmp.png
#		else
#			echo "    Up-to-date"
#		fi
#	done

import os
import argparse
import subprocess

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("-o", "--outdir", default=".", help="Output directory")
	parser.add_argument("filenames", nargs="+", help="SVG files to convert")
	opts = parser.parse_args(args=argv)

	for svg_filename in opts.filenames:
		if opts.verbose:
			print(f"{svg_filename}: ", end="", flush=True)
		png_filename = os.path.join(
			opts.outdir,
			os.path.splitext(os.path.basename(svg_filename))[0] + ".png",
			)
		if not os.path.exists(png_filename) or os.path.getmtime(svg_filename) > os.path.getmtime(png_filename):
			if opts.verbose:
				print("	Generating {png_filename}... ", end="", flush=True)
			try:
				subprocess.run(["rsvg-convert", svg_filename, "-o", ".tmp.png"], check=True)
				subprocess.run(["pngcrush", "-q", ".tmp.png", png_filename], check=True)
			finally:
				if os.path.exists(".tmp.png"):
					os.remove(".tmp.png")
			if opts.verbose:
				print("Done.")
		elif opts.verbose:
			print("{png_filename} is up-to-date.")

	return 0
