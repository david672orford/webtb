"""Convert an SVG icon to PNG in a series of sizes"""

#svg="$1"
#shift 1
#for size in $*
#	do
#	rsvg-convert -w $size -h $size $svg -o .tmp.png
#	pngcrush -q .tmp.png `basename $svg .svg`-${size}x${size}.png
#	rm .tmp.png
#	done

import argparse
import os
from subprocess import run

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("filename", help="The source SVG file")
	parser.add_argument("sizes", nargs="+", type=int, help="One or more icon sizes (e.g., 32 48 64)")
	opts = parser.parse_args(args=argv)

	if opts.verbose:
		print(f"{opts.filename}")
	basename = os.path.splitext(opts.filename)[0]
	for size in opts.sizes:
		output_png = f"{basename}-{size}x{size}.png"
		if opts.verbose:
			print(f" → {output_png}")

		tmp_png = ".tmp.png"
		try:
			run(["rsvg-convert", "-w", str(size), "-h", str(size), opts.filename, "-o", tmp_png], check=True)
			run(["pngcrush", "-q", tmp_png, output_png], check=True)
		finally:
			if os.path.exists(tmp_png):
				os.remove(tmp_png)

	return 0
