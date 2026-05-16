"""Properly quote a filename for use in an href"""

import urllib.parse
import re
import argparse

# Percent encode the pathname. We do not encode comma because
# Libreoffice does not and we do not want to create two forms
# of the same URL.
def quote(pathname):
	return urllib.parse.quote(pathname, safe="/~!$&'()*+,;=:@")

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--html", action="store_true", help="Generate an <a> in an <li>")
	parser.add_argument("filenames", nargs="+", help="Filenames to turn into links")
	opts = parser.parse_args(args=argv)
	for filename in opts.filenames:
		href = quote(filename)
		if opts.html:
			m = re.search(r"([^/]+)\.[a-z0-9]+$", filename)
			assert m
			print('<li><a href="%s">\n\t%s</a></li>' % (href, m.group(1)))
		else:
			print(href)
	return 0
