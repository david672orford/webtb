"""Convert Audacity labels to VTT subtitles"""

import argparse
import os
import lxml.etree as ET

# Read a label track exported from Audacity as a text file.
# Write a WebVTT file.
def labels2webvtt(infd, outfd, index=0, padding=0):
	assert index == 0
	outfd.write("WEBVTT\r\n\r\n")
	id = 0
	for line in infd:
		start, end, text = line.rstrip().split("\t")
		start = float(start.replace(",","."))
		end = float(end.replace(",",".")) + (padding / 1000)
		outfd.write("%d\r\n" % id)
		outfd.write("%02d:%06.3f --> %02d:%06.3f\r\n" % (int(start / 60), start % 60.0, int(end / 60), end % 60.0))
		outfd.write("%s\r\n" % text.replace("|","\r\n"))
		outfd.write("\r\n")
		id += 1

# Read in indicated label track from an AUP file (which is in XML format).
# Write a WebVTT file.
def aup2webvtt(infd, outfd, index=0, padding=0):
	tree = ET.parse(infd)
	outfd.write("WEBVTT\r\n\r\n")
	id = 0
	labeltracks = tree.findall("//{http://audacity.sourceforge.net/xml/}labeltrack")
	labeltrack = labeltracks[index]
	for label in labeltrack:
		assert label.tag.endswith("}label")
		start = float(label.attrib["t"])
		end = float(label.attrib["t1"])
		text = label.attrib["title"]
		outfd.write("%d\r\n" % id)
		outfd.write("%02d:%06.3f --> %02d:%06.3f\r\n" % (int(start / 60), start % 60.0, int(end / 60), end % 60.0))
		outfd.write("%s\r\n" % text.replace("|","\r\n"))
		outfd.write("\r\n")
		id += 1

def main(argv:list[str]) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--verbose", action="store_true", help="Describe actions taken")
	parser.add_argument("infile", help="Audacity .aup or labels file")
	parser.add_argument("outfile", help="VTT file", default=None)
	parser.add_argument("label_track", type=int, help="Track number of label track", default=0)
	parser.add_argument("padding", type=int, help="padding", default=0)
	opts = parser.parse_args(args=argv)

	stem, ext = os.path.splitext(opts.infile)
	assert ext in (".aup", ".txt")
	if opts.outfile is None:
		opts.outfile = stem + ".vtt"

	if opts.verbose:
		print(f"{opts.infile} ")
	with open(opts.infile, "r") as infd:
		with open(opts.outfile, "w") as outfd:
			if opts.infile.endswith(".aup"):
				aup2webvtt(infd, outfd, opts.label_track, opts.padding)
			else:
				labels2webvtt(infd, outfd, opts.label_track, opts.padding)

	return 0
