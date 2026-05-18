"""Convert HTML files to PDF"""

import argparse
import os
from urllib.parse import quote
import base64

from webtb.libs.chromium import CDP

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("--debug", action="store_true", help="Detailed account of interactions with Chrome")
	parser.add_argument("-o", "--outdir", default=".", help="Output directory")
	parser.add_argument("filenames", nargs="+", help="HTML files to convert")
	opts = parser.parse_args(args=argv)

	if opts.debug:
		print(" Starting Chrome...")
	cdp = CDP(opts.debug)

	for filename in opts.filenames:
		if opts.verbose:
			print(f"converting \"{filename}\"...")

		url = "file://" + os.path.abspath(filename)
		outfilename = os.path.join(opts.outdir, os.path.splitext(filename)[0] + ".pdf")

		cdp.navigate(url)

		response = cdp.cmd("Page.printToPDF",
			landscape = False,
			displayHeaderFooter = False,
			scale = 1.0,
			paperWidth = 8.5,
			paperHeight = 11.0,
			marginTop = 0.5,
			marginButtom = 0.5,
			marginLeft = 0.5,
			marginRight = 0.5,
			preferCSSPageSize = True,
			)
		pdf_data = base64.b64decode(response["result"]["data"])
		if opts.verbose:
			print(f" → \"{outfilename}\"")
		with open(outfilename, "wb") as fh:
			fh.write(pdf_data)

	cdp.close()
	return 0
