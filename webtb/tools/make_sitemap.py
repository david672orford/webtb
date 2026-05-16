"""Create a sitemap.xml listing the indicated files"""

import argparse
import os
import datetime
from urllib.parse import quote
import re
from collections import Counter
import json

import lxml.etree as ET
from lxml.etree import tostring
from lxml.builder import E
import lxml.html

def noindex(filename, counter):
	doc = lxml.html.parse(filename)

	for script in doc.getroot().xpath(".//script[@type='application/ld+json']"):
		data = json.loads(script.text)
		for item in data if type(data) is list else (data,):
			counter[item["@type"]] += 1

	for meta in doc.getroot().xpath("./head/meta[@name='robots']"):
		robots = set([i.lower() for i in re.split(r"\s*,\s*", meta.attrib.get("content",""))])
		if "noindex" in robots:
			return True
	return False

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("site_url", help="URL of the root of the website")
	parser.add_argument("filenames", nargs="+", help="Files to include in the sitemap")
	opts = parser.parse_args(args=argv)

	urlset:ET._Element = E.urlset({"xmlns":"http://www.sitemaps.org/schemas/sitemap/0.9"})

	counter = Counter()
	for filename in opts.filenames:
		if noindex(filename, counter):
			counter["excluded"] += 1
			continue
		urlset.append(E.url(
			E.loc(opts.site_url + quote(re.sub(r"/index\.html$", "/", filename))),
			E.lastmod(datetime.datetime.utcfromtimestamp(os.path.getmtime(filename)).isoformat() + "Z")
			))
		counter["included"] += 1

	with open("sitemap.xml", "wb") as fh:
		fh.write(tostring(urlset, pretty_print=True, xml_declaration=True, encoding="UTF-8"))

	if opts.verbose:
		for name in sorted(counter.keys()):
			print("%s: %s" % (name, counter[name]))

	return 0
