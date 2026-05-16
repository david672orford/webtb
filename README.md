# Web Toolbox

This is a set of utilities which help to prepare and verify files for static
websites.

## webtb aup2webvtt

    $ webtb aup2webvtt --verbose

## webtb beautify

    $ webtb beautify --verbose mydoc.html

## webtb encode-audio

Produce MP3 and OGG-Vorbis versions of all the WAV files in the current directory.
Create `outdir` and store the output files in it:

    $ webtb encode-audio -o outdir *.wav

## webtb encode-srcset

Produce versions of all the JPEG files in the current directory and store them
in `outdir`:

    $ webtb encode-srcset --verbose -o outdir *.jpg

## webtb encode-video

    $ webtb encode-video --verbose

## webtb html-diff

    $ webtb file1.html file2.html

## webtb html-linter

Check all the HTML files in the current directory:

    $ webtb html-linter *.html

## webtb make-href

```
$ webtb "My File.html"
My%20File.html
$ webtb --html "My File.html"
<li><a href="My%20File.html">
My File</a></li>
```

## webtb make-sitemap

Create a `sitemap.xml` including all of the HTML files in the current directory:

    $ webtb make-sitemap \*.html

## webtb markdown2html

Create HTML versions of all the markdown files in the current directory:

    $ webtb markdown2html --verbose *.md

## webtb minify

    $ webtb minify --verbose *.js *.css

## webtb precompress-gzip

Create or update .gz versions of all HTML files in the current directory:

    $ webtb precompress-gzip --verbose *.html

## webtb show-metadata

    $ webtb show-metadata index.html video.mp4 

## webtb svg2png

    $ webtb svg2png --verbose -o outdir *.svg

## webtb svg2png-icon

    $ webtb svg2png-icon --verbose icon.svg

## webtb xspf-cat

    $ webtb xspf-cat --verbose -o newplaylist.xspf playlist1.xspf playlist2.xspf

## webtb xspf-youtube

    $ webtb xspf-youtube --verbose playlist.xspf https://www.youtube.com/watch?v=XXXXXXXXXXXX

