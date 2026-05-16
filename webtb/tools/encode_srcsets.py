"""Scale an image to multiple sizes"""

#if [ "$1" != "-o" ]
#	then
#	echo "Usage: $0 -o <outdir> <image>..."
#	exit 1
#	fi
#shift
#
#targetdir="$1"
#shift
#
#for filename in "$@"
#	do
#	basename=`basename "$filename" .jpg`
#	echo "$basename"
#	for resolution in "160x120" "320x240" "640x480" "1280x960"
#		do
#		convert -resize "${resolution}^" \
#			-gravity "Center" \
#			-crop "${resolution}+0+0" \
#			+repage \
#			-quality "80%" \
#			-interlace Plane -strip \
#			"$filename" "${targetdir}/${basename}-${resolution}.jpg"
#		done
#	done

import argparse
import os
from subprocess import run

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("-o", "--outdir", default=".", help="Output directory")
	parser.add_argument("filenames", nargs="+", help="Source JPEG images to process")
	opts = parser.parse_args(args=argv)

	os.makedirs(opts.outdir, exist_ok=True)

	resolutions = ["160x120", "320x240", "640x480", "1280x960"]

	for filename in opts.filenames:
		stem = os.path.splitext(os.path.basename(filename))[0]
		if opts.verbose:
			print(f"{filename}")
		for res in resolutions:
			outfile = os.path.join(opts.outdir, f"{stem}-{res}.jpg")
			print(f" → {outfile}")
			run(["convert",
				"-resize", f"{res}^",
				"-gravity", "Center",
				"-crop", f"{res}+0+0",
				"+repage",
				"-quality", "80%",
				"-interlace", "Plane",
				"-strip",
				filename,
				outfile,
				], check=True)

	return 0
