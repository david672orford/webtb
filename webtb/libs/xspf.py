# bin/xspflib.py
# References:
# http://www.xspf.org/xspf-v1.html

import lxml.etree as ET
from lxml.builder import E

# A track in an XSPF playlist
# TODO: implement link, meta, and extension
class PlaylistItem(object):
	elements = ("location", "title", "creator", "annotation", "info", "image", "album", "trackNum", "duration")
	def __init__(self, track=None, **kwargs):
		if track is not None:
			for name in self.elements:
				el = track.xpath("./xspf:%s" % name, namespaces={"xspf":"http://xspf.org/ns/0/"})
				value = el[0].text if len(el) > 0 else None
				setattr(self, name, value)
		else:
			for name in self.elements:
				setattr(self, name, None)
			for name, value in kwargs.items():
				assert name == "duration_seconds" or name in self.elements, name
				setattr(self, name, value)
		self.duration = int(self.duration)

	@property
	def duration_seconds(self):
		return self.duration / 1000

	@duration_seconds.setter
	def duration_seconds(self, seconds):
		self.duration = seconds * 1000

	def as_element(self):
		track:ET._Element = E.track()
		for el_name in self.elements:
			value = getattr(self, el_name)
			if value is not None:
				el = ET.Element(el_name)
				el.text = str(value)
				track.append(el)
		return track

# The XSPF playlist
# TODO: implement playlist metadata
class Playlist(list):
	def __init__(self, filename=None):
		if filename is not None:
			parser = ET.XMLParser(remove_blank_text=True)
			tree = ET.parse(filename, parser)
			tracklist = tree.getroot().xpath("./xspf:trackList", namespaces={"xspf":"http://xspf.org/ns/0/"})[0]
			for track in tracklist:
				self.append(PlaylistItem(track))

	def save(self, filename):
		tracklist:ET._Element = E.trackList()
		for track in self:
			tracklist.append(track.as_element())
		playlist = E.playlist({'version':'1', 'xmlns':'http://xspf.org/ns/0/'}, tracklist)
		output = ET.tostring(
			playlist,
			encoding='unicode',
			pretty_print=True,
			)
		with open(filename, "w", encoding="utf-8") as fh:
			fh.write(output)
