"""Minify JS and CSS files. Convert SCSS files to CSS."""

# To use, list individual files and directories on the command line.
# Individual files named must exist and have the extension of a supported type.
# Directories will be searched (though not recursively) and supported files
# within them will be processed.
#

import argparse
import os
import sys
import re

from rjsmin import jsmin
from rcssmin import cssmin
from scss import Scss

class UnsupportedResource(Exception):
	pass

def find_jobs(filenames, ignore_unsupported=False):
	jobs = []
	for filename in filenames:
		m = re.search(r"^(.+?)(\.min)?\.([^\./]+)$", filename)
		if m and m.group(2) is None:		# matches and no ".min.",
			processor = {
				"js": ["js", lambda text: jsmin(text)],
				"css": ["css", lambda text: cssmin(text)],
				"scss": ["css", lambda text: cssmin(Scss().compile(text))],
				}.get(m.group(3))
			if processor is not None:
				jobs.append((
					m.group(3),			# input extension
					processor[1],		# processing function
					filename,			# input filename
					"%s.min.%s" % (		# output filename
						m.group(1),		# basename
						processor[0]	# output extension
						)
					))
				continue
		if not ignore_unsupported:
			raise UnsupportedResource("Unsupported resource: %s\n" % filename)
	return jobs

def read_file(filename):
	with open(filename, mode="r", encoding="utf-8") as fh:
		return fh.read()

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("filenames", nargs="+", help="Files (or directories of files) to minimize")
	opts = parser.parse_args(args=argv)

	# Build a list of the conversions to be done
	jobs = []
	try:
		for arg in opts.filenames:
			if os.path.isdir(arg):
				filenames = []
				for filename in os.listdir(arg):
					filenames.append(os.path.join(arg, filename))
				jobs.extend(find_jobs(filenames, ignore_unsupported=True))
			else:
				jobs.extend(find_jobs([arg]))
	except UnsupportedResource as e:
		print(e, file=sys.stderr)
		return 10

	# Perform the conversions on the files in the list
	for ext, processor, inname, outname in jobs:
		if opts.verbose:
			print(f"  {ext}: {inname} → {outname}")

		# Minify
		intext = read_file(inname)
		outtext = processor(intext)

		# If first time, or different result, replace output file.
		existing_outtext = read_file(outname) if os.path.exists(outname) else None
		if existing_outtext != outtext:
			with open(outname, mode="w", encoding="utf-8") as fh:
				fh.write(outtext)

	return 0
