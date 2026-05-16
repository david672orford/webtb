"""Convert Markdown to HTML"""
#
# Python-Markdown (used here)
#   https://github.com/Python-Markdown/markdown
#   https://python-markdown.github.io/
# Commonmark
#   https://github.com/readthedocs/commonmark.py
# Mistletoe
#   https://github.com/miyuchina/mistletoe
#   Claims somewhat higher performance than Python-Markdown
#   and significantly higher performance than Commonmark.
#

import argparse
import os
from functools import lru_cache

from markdown import markdown
from yaml import safe_load as load_yaml
import jinja2

# Container for site or page metadata
class MetaData(dict):
	def __getattr__(self, name):
		return self.get(name, None)
	def __setattr__(self, name, value):
		self[name] = value

class TemplateLoader:
	def __init__(self, template_dir:str):
		self.template_env = jinja2.Environment(
			loader = jinja2.FileSystemLoader(
				searchpath = template_dir
				)
			)
	@lru_cache
	def load(self, template):
		return self.template_env.get_template(template)

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("filenames", nargs="+", help="Files to convert")
	opts = parser.parse_args(args=argv)

	# Load site configuration
	site = MetaData()
	config_file = "webtb-markdown2html.conf"

	if os.path.exists(config_file):
		if opts.verbose:
			print(f"Loading {config_file}")
		with open(config_file, mode="r", encoding="utf-8") as conf:
			site.update(load_yaml(conf))
	elif opts.verbose:
		print("Using default configuration.")

	if site.template_dir is None:
		site.template_dir = os.path.join(os.path.dirname(config_file), "templates")
	if opts.verbose:
		print(f"Template directory: {site.template_dir}")
	template_loader = TemplateLoader(site.template_dir)

	# Convert all of the Markdown files named on the command line into HTML files placed alongside them
	for filename in opts.filenames:
		stem, ext = os.path.splitext(filename)
		assert ext == ".md"		# FIXME
		output_filename = f"{stem}.html"
		if opts.verbose:
			print(f"{filename} → {output_filename}")

		# Open the markdown source file
		with open(filename, mode="r", encoding="utf-8") as infile:
			text = infile.read()

		# Split off and parse YAML metadata at start
		page = MetaData()
		if text.startswith("---\n"):
			parts = text.split("---\n")
			page.update(load_yaml(parts[1]))
			content = parts[2]
		else:
			content = text

		# Convert markdown to HTML
		content = markdown(content, extensions=[
			"md_in_html",	# markdown="1"
			"attr_list",
			"def_list",		# <dl>
			"fenced_code",
			"footnotes",
			"tables",
			])

		# Load the template specified in this page's metadata or (if none
		# is specified), the site's default template.
		template_name = page.template or site.template or "default.html"
		if opts.verbose:
			print(f" {template_name}")
		template = template_loader.load(template_name)

		# Insert the HTML (and the metadata) into the page template
		html = template.render(site=site, page=page, content=content)

		# Write finished HTML file
		with open(output_filename, mode="w", encoding="utf-8") as outfile:
			outfile.write(html)

		output_filename_gz = output_filename + ".gz"
		if os.path.exists(output_filename_gz):
			os.unlink(output_filename_gz)

	return 0
