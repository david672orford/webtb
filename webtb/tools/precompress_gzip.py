"""Create or update pre-compressed files for the webserver (gzip)"""

# Gzip compress the files name on the command line putting the compressed
# versions alongside the originals. Compares dates to figure out which
# compressed copies are out-of-date.
#
# Uses Zopfli:
# https://github.com/google/zopfli

import argparse
import sys
import os
import subprocess

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("filenames", nargs="+", help="Files to be precompressed")
	opts = parser.parse_args(args=argv)

	files_compressed = 0
	files_recompressed = 0
	files_total = 0
	for filename in opts.filenames:
		if filename.endswith(".gz"):
			continue
		if filename.endswith("~"):
			continue

		if opts.verbose:
			print(f"\"{filename}\": ", end="", flush=True)
		filename_output = "%s.gz" % filename
		filename_mtime = os.path.getmtime(filename)

		if not os.path.exists(filename_output):
			if opts.verbose:
				print("compressing...")
			go = True
			files_compressed += 1
		elif os.path.getmtime(filename_output) < filename_mtime:
			if opts.verbose:
				print("recompressing...")
			go = True
			files_recompressed += 1
		else:
			if opts.verbose:
				print("gz is up-to-date.")
			go = False
		files_total += 1

		if go:
			output = None
			try:
				output = subprocess.check_output(
					("zopfli", "-i1000", filename),
					stderr=subprocess.STDOUT
					)
			except subprocess.CalledProcessError:
				print("    failed: non-zero exit code", file=sys.stderr)
				print(output, file=sys.stderr)
				return 1

			# Set the modification time of the output file to 10ms after the
			# modification time of the source file. This avoids strange errors
			# which we think are caused by the resolution of the mtime which
			# were causing unnecessary rebuilding.
			os.utime(filename_output, (filename_mtime + 0.01, filename_mtime + 0.01))

	print("Compressed %d and recompressed %d of %d files" % (files_compressed, files_recompressed, files_total))
	return 0
