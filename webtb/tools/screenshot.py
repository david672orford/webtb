"""Take screenshots of webpages"""
# References:
# https://chromedevtools.github.io/devtools-protocol/
# https://github.com/fate0/pychrome/

import argparse
from time import sleep
import base64
import struct

from webtb.libs.chromium import CDP

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("--debug", action="store_true", help="Detailed account of interactions with Chrome")
	parser.add_argument("-o", "--output", help="Output PNG filename")
	parser.add_argument("url", help="URL to load and screenshot")
	opts = parser.parse_args(args=argv)

	if opts.verbose:
		print(f"Screenshotting \"{opts.url}\"...")
	cdp = CDP(opts.debug)
	cdp.navigate(opts.url)

	response = cdp.cmd("Page.captureScreenshot",
		format="png",
		captureBeyondViewport=True,
		)
	img_data = base64.b64decode(response["result"]["data"])
	if opts.verbose:
		width, height = struct.unpack(">II", img_data[16:24])
		print(f" → \"{opts.output}\" ({width}x{height}, {len(img_data)} bytes)")
	with open(opts.output, "wb") as fh:
		fh.write(img_data)

	cdp.close()
	return 0
