import json
import re
from textwrap import indent

import lxml.etree as ET
from lxml import html as HTML
import jsbeautifier
import cssbeautifier

# FIXME: not used yet
inline_elements = (
	"span",
	"a",
	"b",
	"i",
	"em",
	)

# Alter the whitespace in the element tree to indent the tags
# https://web.archive.org/web/20200130163816/http://effbot.org/zone/element-lib.htm#prettyprint
def indent_html(elem, level=0):
	spaces = "\n" + level*" "
	if len(elem):	# has children

		# If no non-whitespace text,
		if not elem.text or not elem.text.strip():
			if elem.tag in ("li",):
				elem.text = ""
			else:
				elem.text = spaces + " "

		# If no non-whitepace tail,
		if not elem.tail or not elem.tail.strip():
			elem.tail = spaces

		# Do the same for children, indenting one level deeper
		for child in elem:
			indent_html(child, level+1)

	else:			# no children
		if level and (not elem.tail or not elem.tail.strip()):
			elem.tail = spaces

def indent_cdata(el):
	previous = el.getprevious()
	if previous is not None:
		spaces = previous.tail
	else:
		spaces = el.getparent().text
	assert re.match(r"^\n *$", spaces)
	spaces = spaces[1:]
	el.text = "\n" + indent(el.text.strip(), spaces + "  ") + "\n" + spaces

def pretty_js(text):
	options = jsbeautifier.default_options()
	options.indent_size = 2
	return jsbeautifier.beautify(text, options)

def pretty_json(text):
	obj = json.loads(text)
	return json.dumps(obj, indent=2)

def pretty_css(text):
	options = cssbeautifier.default_options()
	options.indent_size = 2
	return cssbeautifier.beautify(text, options)

def pretty_html(infh, outfh):
	tree = HTML.parse(infh)
	html = tree.getroot()
	assert html.tag == "html"
	indent_html(html)
	for script in html.xpath(".//script"):
		mimetype = script.attrib.get("type")
		if mimetype == "application/ld+json":
			script.text = pretty_json(script.text)
		else:
			script.text = pretty_js(script.text)
		indent_cdata(script)
	for style in html.xpath(".//style"):
		style.text = pretty_css(style.text)
		indent_cdata(style)
	tree.write(outfh, encoding="utf-8", pretty_print=True, method="html")
