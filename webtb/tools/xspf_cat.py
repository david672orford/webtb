"""Concatenate XSPF playlists"""

import argparse
from webtb.libs.xspf import Playlist

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("-o", dest="output_filename", help="Output filename")
	parser.add_argument("filenames", nargs="+", help="Playlists to concatenate")
	opts = parser.parse_args(args=argv)

	outpl = Playlist()
	for filename in opts.filenames:
		if opts.verbose:
			print(f" {filename}")
		inpl = Playlist(filename)
		for track in inpl:
			outpl.append(track)
	outpl.save(opts.output_filename)
	return 0
