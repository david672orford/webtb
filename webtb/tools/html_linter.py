"""Test HTML files for conformance to requirements"""
#
# This script checks HTML files for conformance to style. In particular:
# * That the charset is defined as utf-8 at the top of the <head>
# * That there is an <h1> with the same text as the <title>
# * Mime type is defined in certain cases
# * Local 'resources' actually exist
# * Images have alt text
#
# TODO
# * more easily configurable analytics-vX test
# * should we keep the hide_nav test?

import argparse
import sys
import os
import lxml.html
from urllib.parse import quote, unquote, urlparse
import re
import subprocess
import io
import json
from collections import Counter

# References:
# https://docs.python.org/2/library/xml.etree.elementtree.html
# http://lxml.de/lxmlhtml.html

extension2mimetype = {
	"txt":   "text/plain",
	"html":  "text/html",
	"xhtml": "application/xhtml+xml",
	"php":   "text/html",				# just a guess
	"cgi":   "text/html",				# just a guess
	"pdf":   "application/pdf",
	"odt":   "application/vnd.oasis.opendocument.text",
	"ogg":   "audio/ogg",
	"mp3":   "audio/mpeg",
	"webm":  "video/webm",
	"mp4":   "video/mp4",
	"svg":   "image/svg+xml",
	"png":   "image/png",
	"jpg":   "image/jpeg",
	"epub":  "application/epub+zip",
	}

def check_html(filename, options):
	base = os.path.dirname(filename)
	root, head, body = open_doc(filename)

	# Check <html> tag
	if not "lang" in root.attrib:
		warning("html: no lang attribute")

	# Check <head> tag and its <meta> children
	if len(head) == 0:
		raise HtmlError("Empty <head>")
	head1 = head[0]
	if head1.tag != "meta":
		warning("First child of <head> is not <meta>")
	else:
		if head1.attrib.get("http-equiv","").lower() == "content-type" \
				and re.match(r"text/html; *charset=utf-8", head1.attrib.get("content","")):
			pass
		elif not "charset" in head1.attrib:
			warning("First <meta> does not specify charset")
		elif head1.attrib["charset"] != "utf-8":
			warning("First <meta> specifies charset %s instead of UTF-8" % head1.attrib["charset"])

	# Check <head> -> <title>
	title_text_variants = set()
	title_text = find_one(head, "title").text
	if title_text is not None:
		title_text_variants.add(title_text)
		m = re.match(r"^[^:]+:\s(.+)$", title_text)
		if m:
			title_text_variants.add(m.group(1))
			m = re.search(r"—(.+)$", m.group(1))	# without category name (which comes before em dash)
			if m:
				title_text_variants.add(m.group(1))

	# Check <body> ... <h1>
	h1 = body.find(".//h1")
	if h1 is not None:
		h1_text = h1.text_content().strip()
		if h1_text.startswith("<\xa0"):
			h1_text = h1_text[2:]
		elif h1_text.startswith("< "):
			warning("Character after arrow in <h1> back link is not &nbsp;")
			h1_text = h1_text[2:]		# so as not to trigger more confusing warnings
		if not h1_text in title_text_variants:
			warning("<h1> text does not match <title>: \"%s\" vs \"%s\"" % (h1_text, str(title_text_variants)))

	# Check other tags in <head>
	script_counter = Counter()
	meta_name_items = {}				# <meta name="description" content="A cool webpage">
	meta_opengraph_items = {}			# <meta property="og:site_name" content="example.com">
	for el in head.findall("./*"):
		if options.debug:
			print("  %s: %s" % (el.tag, str(el.attrib)))

		if el.tag == "meta":
			if "name" in el.attrib:
				meta_name_items[el.attrib["name"]] = el.attrib.get("content")
			if "property" in el.attrib:
				meta_opengraph_items[el.attrib["property"]] = el.attrib.get("content")

		elif el.tag == "title":			# checked above
			pass

		elif el.tag == "link":
			href = el.attrib["href"]
			if not href:
				warning("link: href lacking")
			elif not url_is_remote(href):
				if not local_url_is_good(base, href):
					warning("link: resource does not exist: %s" % href)
				if not url_quoting_is_good(href):
					warning("link: href: odd_quoting: %s" % href)
			if not "rel" in el.attrib:
				warning("link: lacks rel attribute: %s" % str(el.attrib))
			elif el.attrib["rel"] == "stylesheet":
				if not "type" in el.attrib:
					warning("link: stylesheet type is not specified: %s" % el.attrib.get("type"))
				elif el.attrib["type"] != "text/css":
					warning("link: stylesheet type is not text/css: %s" % el.attrib.get("type"))

		elif el.tag == "script":
			if el.text is not None and len(el.text) < 100 and "hide_nav" in el.text:
				if el.text != 'parent===window||(document.documentElement.className="hide_nav")':
					warning("non-standard hide_nav text")
			else:
				check_script(el, base, script_counter)

		elif el.tag == "style":
			if not "type" in el.attrib:
				warning("style: lacks type attribute: %s" % str(el.attrib))
			elif el.attrib["type"] != "text/css":
				warning("style: type is not text/css: %s" % el.attrib["type"])

		elif el.tag == "base":
			href = el.attrib.get("href")
			if href is not None:
				assert href.startswith(".")		# other possibilities not implemented yet
				base = unquote(os.path.join(base, href))

		else:
			warning("Unexpected item in <head>: %s" % el.tag)

	# Check body header
	if len(body.findall(".//h1")) > 0 and len(body.findall(".//header")) == 0:
		warning("has <h1> but no <header>")

	# Check scripts in <body>
	for el in body.findall(".//script"):
		if el.text is not None and "hide_nav" in el.text:
			warning("script: hide_nav code should be in <head>, not <body>")
		else:
			check_script(el, base, script_counter)

	# Check <img> tags in <body>
	for el in body.findall(".//img"):
		if options.debug:
			print("  %s: %s" % (el.tag, str(el.attrib)))
		src = el.attrib.get("src")
		if not src:
			warning("img: lacks src attribute")
		else:
			if src.startswith("data:"):
				pass
			else:
				if not url_is_remote(src):
					if not local_url_is_good(base, src):
						warning("img: image does not exist: %s" % src)
					if not url_quoting_is_good(src):
						warning("img: src: odd quoting: %s" % src)
				if not "type" in el.attrib:
					warning("img: lacks type attribute: %s" % str(el.attrib))
				elif not el.attrib["type"].startswith("image/"):
					warning("img: type is not text/*: %s" % el.attrib["type"])
			if not "alt" in el.attrib:
				id = el.attrib.get("id")
				src = el.attrib.get("src")
				if len(src) > 40:
					src = src[:40] + "..."
				warning("img: lacks alt attribute: %s %s" % (id, src))
			elif el.attrib["alt"].strip() == "":
				warning("img: alt attribute has empty value")

	# Check <a> tags in <body>
	for el in body.findall(".//a"):
		check_hyperlink(base, el, options)

	# Check <form> tags in <body>
	for el in body.findall(".//form"):
		action = el.get("action")
		if action is not None and not url_is_remote(action):
			if not local_url_is_good(base, action):
				warning("form: action does not exist: %s" % action)
			if not url_quoting_is_good(action):
				warning("form: action: odd quoting: %s" % action)

	# Check <audio> tags in <body>
	for el in body.findall(".//audio"):
		check_player(el, base)

	# Check <video> tags in <body>
	for el in body.findall(".//video"):
		check_player(el, base)

	# Check SeeAlso frames in <body>
	for el in body.findall(".//div"):
		if el.attrib.get("class","").startswith("fr"):
			if el.attrib.get("id") != "SeeAlso" and "See Also" in el.text_content():
					warning("div: id should be SeeAlso")

	#---------------------------------------
	# analyze the metadata
	#---------------------------------------

	if not "viewport" in meta_name_items:
		warning("Viewport not set")

	# If there is even one Opengraph tag, make sure all of the mandatory tags are present.
	if(len(meta_opengraph_items)) > 0:
		for og_item in ("og:site_name", "og:type", "og:title", "og:image"):
			if not og_item in meta_opengraph_items:
				warning("Required Opengraph element missing: %s" % og_item)

	if "og:image" in meta_opengraph_items:
		url = meta_opengraph_items["og:image"]
		if not local_url_is_good(base, url, full=True):
			warning("og:image: not found: %s" % url)

	# Unless robots have been told not to include this page in their indexes,
	# check to see that it has descriptive meta tags.
	robots = set([i.lower() for i in re.split(r"\s*,\s*", meta_name_items.get("robots",""))])
	if not "noindex" in robots:
		if not "description" in meta_name_items:
			warning("no meta description")
		if not "keywords" in meta_name_items:
			warning("no meta keywords")
		if not "BreadcrumbList" in script_counter and not "WebSite" in script_counter:
			warning("no Schema.org BreadcrumbList")

	if not "analytics" in script_counter:
		warning("no analytics")

def open_doc(filename, query=""):

	if filename.endswith(".cgi"):
		env={
			"GATEWAY_INTERFACE":"CGI/1.1",
			"QUERY_STRING":query
			}
		cgi = subprocess.run(os.path.abspath(filename), env=env, cwd=os.path.dirname(filename), stdout=subprocess.PIPE)
		output = cgi.stdout.decode("utf-8").replace("\r","")
		output = output.split("\n\n",1)[1]
		doc = lxml.html.parse(io.StringIO(output))
	else:
		with open(filename) as fh:
			doc = lxml.html.parse(fh)

	if doc.docinfo.doctype != "<!DOCTYPE html>":
		warning("Missing or obsolete doctype")
		if "Frameset" in doc.docinfo.doctype:
			return

	root = doc.getroot()
	if root is None or root.tag != "html":
		raise HtmlError("Not an HTML document")

	count = len(root.findall("."))
	if count != 1:
		raise HtmlError("Root contains %d element(s), 1 expected" % count)

	head = find_one(root, "head")
	body = find_one(root, "body")

	return root, head, body

# Make sure an <a> element conforms to our standards.
def check_hyperlink(base, el, options):
	href =  el.attrib.get("href")
	if href is None:
		warning("a: no href")
		return
	if options.debug:
		print("  %s: %s" % (el.tag, href))

	if href.startswith("#"):					# FIXME: why not test?
		return

	parsed_url = urlparse(href)
	if parsed_url.scheme == "mailto":
		return

	# Make sure type is declared for non-HTML files (identified by extension).
	m = re.search(r"\.([^/\.]+)$", parsed_url.path)
	if m:
		filename_ext = m.group(1)
		expected_mimetype = extension2mimetype.get(filename_ext)
		if expected_mimetype == "text/html":
			pass
		elif expected_mimetype == "application/xhtml+xml":
			pass
		elif not "type" in el.attrib:
			warning("a: link to %s file is lacking type attribute: %s" % (filename_ext.upper(), str(el.attrib)))
		elif el.attrib["type"] != expected_mimetype:
			warning("a: type of link to %s file is not %s: %s" % (filename_ext.upper(), expected_mimetype, el.attrib["type"]))

	# Tests after this we will perform only on our own URLs.
	if url_is_remote(href):
		return

	if not local_url_is_good(base, href):		# not broken link
		warning("a: broken link: %s" % str(el.attrib))

	if not url_quoting_is_good(href):			# correct use of percent quoting
		warning("a: href: odd quoting: %s" % href)

	if re.search(r"\.$", href):					# FIXME: detect ".", "..", "/..", etc.
		warning("a: href to directory does not end with slash: %s" % href)
		return

	# If link is to an HTML document, make sure the hyperlinked text is reasonable.
	if el.attrib.get("type","text/html") == "text/html":

		# The hyperlinked text
		link_text = el.text_content().strip()

		# We will forgive an original hyperlinked text as long as the title attribute
		# (which is generally displayed on hover) matches the title of the document.
		link_title = el.attrib.get("title")

		# Open the document and extract what we consider reasonable 'names' for it.
		# Also get a list of its fragments in case this turns out to be a 'back'
		# navigation link.
		acceptable_titles, probable_fragments = scan_document(base, parsed_url)

		# If this is a 'back' navigation link and the target document has
		# sections with fragment identifiers, make sure the 'back' link
		# points to one of them. That way 'back' takes us to the part of
		# the index which lists this document.
		# Note that here we accept both "<&nbsp;" and "< " as backlinks
		# because we print a warning about "< " elsewhere.
		if link_text.startswith("<\xa0") or link_text.startswith("< "):
			if parsed_url.fragment == "":
				if len(probable_fragments) > 0:
					warning("a: back link href has no fragment: %s" % href)
			else:
				if not parsed_url.fragment in probable_fragments:
					warning("a: fragment not found: %s" % href)

		# Otherwise compare linked text to title of document to which it is linked.
		#elif link_text != "" or (link_title != "" and len(el.xpath(".//img")) > 0):
		elif link_text != "" or link_title is not None:
			link_texts = set()
			if link_text != "":
				link_texts.add(link_text)
			if link_title is not None:
				link_texts.add(link_title)
			if len(link_texts & acceptable_titles) == 0:
				warning("a: link text mismatch: %s vs target title %s" % (str(link_texts), str(acceptable_titles)))
			if parsed_url.fragment != "" and not parsed_url.fragment in probable_fragments:
				warning("a: fragment not found as a <section>: %s" % href)

		else:
			warning("a: empty linked text: %s" % el.attrib)

	# Slides
	if re.search(r"^\.\./Slides/.+", href) and el.attrib.get("target") != "slide_viewer":
		warning("a: target is not slide_viewer: %s" % el.attrib)

# Make sure a <script> tag is good.
def check_script(el, base, counter):
	assert el.tag == "script"
	src = el.attrib.get("src")
	if src:
		if not url_is_remote(src):
			if not local_url_is_good(base, src):
				warning("script: script does not exist: %s" % src)
			if not url_quoting_is_good(src):
				warning("script: href: odd quoting: %s" % src)
		if "/analytics-v" in src:
			counter["analytics"] += 1
			if not ".min." in src:
				warning("script: analytics not minimized")
			if not "-v4." in src:
				warning("obsolete analytics")
			if not "async" in el.attrib:
				warning("analytics not async")
	if not "type" in el.attrib:
		warning("script: lacks type attribute: %s" % str(el.attrib))
	elif el.attrib["type"] == "text/javascript":
		pass
	elif el.attrib["type"] == "application/ld+json":
		data = json.loads(el.text)
		for item in data if type(data) is list else (data,):
			counter[item["@type"]] += 1
	else:
		warning("script: unexpected type: %s" % el.attrib["type"])
	if "href" in el.attrib:
		if "analytics" in el.attrib["href"] and not "async" in el.atttrib:
			warning("script: analytics loaded without async")

	return counter

# Make sure an <audio> or <video> tag is good.
def check_player(el, base):
	assert el.tag == "audio" or el.tag == "video"
	src = el.attrib.get("src")
	if src:
		if not url_is_remote(src):
			if not local_url_is_good(base, src):
				warning("%s: src does not exist: %s" % (el.tag, src))
			if not url_quoting_is_good(src):
				warning("%s: src: odd quoting: %s" % (el.tag, src))
		if not 'type' in el.attrib:
			warning("%s: lacks type attribute" % (el.tag))
		if not url_quoting_is_good(src):
			warning("%s: src: odd quoting: %s" % (el.tag, src))

	poster = el.attrib.get("poster")
	if poster and not url_is_remote(poster):
		if not local_url_is_good(base, poster):
			warning("%s: poster does not exist: %s" % (el.tag, poster))
		if not url_quoting_is_good(poster):
			warning("%s: poster: odd quoting: %s" % (el.tag, poster))

	for el2 in el.findall(".//source"):
		src = el2.attrib.get("src")
		if src and not url_is_remote(src):
			if not local_url_is_good(base, src):
				warning("%s: src does not exist: %s" % (el2.tag, src))
			if not url_quoting_is_good(src):
				warning("%s: src: odd quoting: %s" % (el2.tag, src))
		if not "type" in el2.attrib:
			warning("%s: lacks type attribute" % (el2.tag))

# Does this URL include a domain?
def url_is_remote(url):
	return re.match(r"[a-z]+:", url) or url.startswith("//")

# Test an internal href to make sure it is not broken.
def local_url_is_good(base, url, full=False):
	parsed_url = urlparse(url)
	if full:
		if parsed_url.scheme == "" or parsed_url.netloc == "":
			return False
	path = unquote(parsed_url.path)
	if path.startswith("/"):
		path = path[1:]
	else:
		path = os.path.join(base, path)
	return os.path.exists(path.encode("utf-8"))

# Make sure that the pathname of this URL is quoted no more than necessary.
def url_quoting_is_good(url):
	parsed_url = urlparse(url)
	# See RFC https://tools.ietf.org/html/rfc3986#section-3.3
	expected_path = quote(unquote(parsed_url.path), safe="/~!$&'()*+,;=:@")
	return (parsed_url.path == expected_path)

# Parse an HTML file and extract a list of what we consider to be
# reasonable possible link texts and fragment identifiers.
def scan_document(base, parsed_url):

	# Find the file cooresponding to this URL
	filename = os.path.join(base, unquote(parsed_url.path))
	if filename.endswith("/"):
		for index in ("index.html", "index.cgi"):
			candidate = "%s/%s" % (filename, index)
			if os.path.isfile(candidate):
				filename = candidate
				break

	# Open and parse it.
	root, head, body = open_doc(filename, parsed_url.query)

	# Set of acceptable titles goes here.
	possible_titles = set()

	# List of plausible fragment identifiers for this document goes here.
	fragments = set()

	# Start with <title> tag contents
	title_text = find_one(head, "title").text.strip()

	m = re.search(r"^[^:]+:\s*(.+)$", title_text)		# Remove site name
	if m:
		title_text = m.group(1)
	possible_titles.add(title_text)

	m = re.search(r"^(.+)\s+\([^\(\)]+\)$", title_text)	# With optional subtitle in parenthesis removed
	if m:
		possible_titles.add(m.group(1))

	m = re.search(r"—(.+)$", title_text)				# Without category name (which comes before em dash)
	if m:
		title_text = m.group(1)
		possible_titles.add(title_text)

	m = re.search(r"^Download (.+)$", title_text)
	if m:
		possible_titles.add(m.group(1))

	m = re.search(r"^(.+) on Youtube$", title_text)
	if m:
		possible_titles.add(m.group(1))

	# Take <h1> tag contents too
	h1 = body.find(".//h1")
	if h1 is not None:
		h1_text = h1.text_content().strip()
		if h1_text.startswith("<\xa0"):
			h1_text = h1_text[2:]
		possible_titles.add(h1_text)

	# If the URL given for this document includes a fragment identifier,
	# we will consider an <h2> inside the element with that ID to be
	# a valid title.
	if parsed_url.fragment != "":
		section = body.xpath(".//*[@id='%s']" % parsed_url.fragment)
		if section:
			h2 = section[0].xpath(".//h2")
			if h2:
				h2_text = h2[0].text_content().strip()
				possible_titles.add(h2_text)
				m = re.search(r"^(.+)\s+\([^\(\)]+\)$", h2_text)	# With optional subtitle in parenthesis removed
				if m:
					possible_titles.add(m.group(1))

	# Find any sections in the document and save their ID attributes
	# as possible fragment identifiers.
	for el in body.xpath(".//section") + body.xpath(".//footer"):
		id = el.attrib.get("id")
		if id is not None:
			fragments.add(id)

	# Find spans which indicate subject index entries and add them
	# as possible fragment identifiers too.
	for el in body.xpath(".//span"):
		id = el.attrib.get("id")
		if id is not None and id.startswith("idx"):
			fragments.add(id)

	return possible_titles, fragments

# Find a tag of which there should be only one. We use this
# to find <head>, <body>, etc.
def find_one(parent, tagname):
	found = parent.findall(tagname)
	if len(found) == 1:
		return found[0]
	else:
		raise HtmlError("%d <%s>s when one expected" % (len(found), tagname))

# Used if a severe problem is found such as the file does not exist,
# the format is not HTML, or it is badly damaged.
class HtmlError(Exception):
	pass

# Print the word "Warning" in red followed by the supplied message in bold
color_bold_red = "\033[1;31m"
color_reset = "\033[0m"
color_bold = "\033[1m"
def warning(message):
	print("  %sWarning:%s%s %s%s" % (
		color_bold_red,
		color_reset,
		color_bold,
		message,
		color_reset
		))

# Test all the files named on the command line
def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--debug", action="store_true", help="Print debugging info")
	parser.add_argument("filenames", nargs="+", help="HTML files to check")
	opts = parser.parse_args(args=argv)
	try:
		for filename in opts.filenames:
			print(filename)
			check_html(filename, opts)
	except (HtmlError, FileNotFoundError) as e:
		print("  Error: %s" % e)
		return 1
	return 0
