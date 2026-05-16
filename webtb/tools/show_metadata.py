"""Print metadata from audio, video, raster image, and SVG files"""

import argparse
import os
import sys
import re
import subprocess
import json

from PIL import Image
from PIL.ExifTags import TAGS as ExifTags
import lxml.etree as ET
import lxml.html

def print_html_metadata(filename):
	html = lxml.html.parse(filename)
	head = html.xpath("./head")[0]
	for meta in head.xpath("./meta"):
		print(meta.attrib)
	for script in head.xpath("./script[@type='application/ld+json']"):
		schema_metadata = json.loads(script.text)
		print(json.dumps(schema_metadata, indent=2))

def print_audio_metadata(filename):
	print_video_metadata(filename)

def print_video_metadata(filename):
	args = "ffprobe -v quiet -print_format json -show_format -show_streams".split(" ")
	args.append(filename)
	ffprobe = subprocess.check_output(args).decode("utf-8")
	#print(ffprobe)
	ffprobe = json.loads(ffprobe)
	print(" Duration: %s" % ffprobe["format"]["duration"])
	print(" File Size: %.1f MB" % (float(ffprobe["format"]["size"]) / 1024 / 1024))
	print(" Total Bit Rate: %d kbps" % (int(ffprobe["format"]["bit_rate"]) / 1000))
	for stream in ffprobe["streams"]:
		if stream["codec_type"] == "video":
			print(" Video Codec: %s" % stream["codec_name"])
			print("  Profile: %s" % stream.get("profile",""))
			print("  Aspect Ratio: %s" % stream["display_aspect_ratio"])
			print("  Frame Size: %dx%d" % (stream["width"], stream["height"]))
			print("  Frame Rate: %s" % stream["avg_frame_rate"])
			print("  Pixel Format: %s" % stream["pix_fmt"])
			if "bit_rate" in stream:
				print("  Bit Rate: %d kbps" % (int(stream["bit_rate"]) / 1000))
				print("  BPP: %.2f" % (float(stream["bit_rate"]) / (stream["width"] * stream["height"]) / 30))
	for stream in ffprobe["streams"]:
		if stream["codec_type"] == "audio":
			print(" Audio Codec: %s" % stream["codec_name"])
			print("  Channels: %s" % stream["channels"])
			print("  Sample Rate: %s" % stream["sample_rate"])
			if "bit_rate" in stream:
				print("  Bit Rate: %d kbps" % (int(stream["bit_rate"]) / 1000))
	print(" Tags:")
	tags = ffprobe["format"].get("tags", {})
	for name in sorted(tags.keys()):
		print("  %s: %s" % (name, tags[name]))

def print_raster_metadata(filename):
	img = Image.open(filename)
	for name, value in img.info.items():
		if name == "exif":
			print("  Exif:")
			for exif_name, exif_value in img._getexif().items():
				exif_name = ExifTags.get(exif_name,exif_name)
				print("    %s: %s" % (exif_name, exif_value))
		else:
			print("  %s: %s" % (name, value))

def print_svg_metadata(filename):
	svg_namespaces = {
		"http://www.w3.org/2000/svg": "svg",
		"http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
		"http://web.resource.org/cc/": "cc",
		"http://creativecommons.org/ns#": "cc",
		"http://purl.org/dc/elements/1.1/": "dc"
		}
	def lxml_denamespace(root, namespaces):
		for el in root.iter():
			m = re.match(r"^{([^}]+)}(.+)$", el.tag)
			assert m
			if m.group(1) in namespaces:
				el.tag = "%s_%s" % (namespaces[m.group(1)], m.group(2))
			for name, value in el.attrib.items()[:]:
				m = re.match(r"^{([^}]+)}(.+)$", name)
				if m:
					if m.group(1) in namespaces:
						el.attrib["%s_%s" % (namespaces[m.group(1)], m.group(2))] = value
						del el.attrib[name]
	tree = ET.parse(filename)
	lxml_denamespace(tree, svg_namespaces)
	metadata = tree.xpath("./svg_metadata/rdf_RDF")
	if metadata:
		metadata = metadata[0]
		agent = metadata.xpath("./cc_Work/dc_publisher/cc_Agent/dc_title")
		print("  Agent: %s" % (agent[0].text if agent else "?"))
		source = metadata.xpath("./cc_Work/dc_source")
		print("  Source: %s" % (source[0].text if source else "?"))
		license = metadata.xpath("./cc_License")
		print("  License: %s" % (license[0].attrib["rdf_about"] if license else "?"))

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("filenames", nargs="+", help="Files (or directories of files) to minimize")
	opts = parser.parse_args(args=argv)
	for filename in opts.filenames:
		if opts.verbose:
			print(f"{filename}")
		extension = os.path.splitext(filename)[1]
		if extension == ".html":
			print_html_metadata(filename)
		elif extension in (".wav", ".mp3", ".ogg"):
			print_audio_metadata(filename)
		elif extension in (".mp4", ".webm", ".ts", ".avi", ".mkv"):
			print_video_metadata(filename)
		elif extension in (".png", ".jpg"):
			print_raster_metadata(filename)
		elif extension == ".svg":
			print_svg_metadata(filename)
		else:
			print(f"  File format not supported: {extension}", file=sys.stderr)
	return 0
