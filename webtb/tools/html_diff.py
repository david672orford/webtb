"""Find differences between HTML files"""

import argparse
import sys
import io
from difflib import unified_diff

from webtb.libs.pretty import pretty_html

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("filename1", help="First file to compare")
	parser.add_argument("filename2", help="Second file to compare")
	opts = parser.parse_args(args=argv)

	file1_bytes = io.BytesIO()
	with open(opts.filename1, "rb") as fh:
		pretty_html(fh, file1_bytes)

	file2_bytes = io.BytesIO()
	with open(opts.filename2, "rb") as fh:
		pretty_html(fh, file2_bytes)

	file1_bytes.seek(0)
	file2_bytes.seek(0)

	file1 = io.TextIOWrapper(file1_bytes, encoding="utf-8")
	file2 = io.TextIOWrapper(file2_bytes, encoding="utf-8")

	lines1 = file1.readlines()
	lines2 = file2.readlines()

	diff = unified_diff(lines1, lines2, fromfile=opts.filename1, tofile=opts.filename2)

	lines = 0
	for line in diff:
		sys.stdout.write(line)
		lines += 1

	return 1 if lines > 0 else 0
