"""Pretty print HTML (TODO: CSS, JS)"""

import argparse
import sys
from ..libs.pretty import pretty_html

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("filenames", nargs="+", help="Files to pretty print")
	opts = parser.parse_args(args=argv)
	for filename in opts.filenames:
		with open(filename, "rb") as fh:
			pretty_html(fh, sys.stdout.buffer)
	return 0
