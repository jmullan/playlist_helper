#!/usr/bin/env python -S
import logging
import os
import re
import sys
from optparse import OptionParser

from playlistcreator import PlaylistCreator

sample = """
"Snack Attack" - Godley & Creme
"""

sample_json = """
[{
"Title": "Booty Clap (Mr. Sche remix)",
"Artist": "Kool Keith",
"Album": "The Legend of Tashan Dorrsett",
}]
"""

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def match(regex, line):
    match = None
    matches = re.match(regex, line)
    if matches:
        match = {}
        for key in ['artist', 'album', 'track']:
            try:
                match[key] = matches.group(key)
            except IndexError:
                pass
    return match


def process_txt(pc, options, filename):
    if not os.path.isfile(filename):
        logger.error('Not a file: %s', filename)
        return

    playlist_name = os.path.splitext(os.path.basename(filename))[0]

    playlist_description = options.get('description')
    if playlist_description is None:
        playlist_description = 'Songs about %s' % playlist_name

    contents = ''
    filesize = os.path.getsize(filename)
    with open(filename) as f:
        contents = f.read(filesize).decode('utf8')
    if not contents:
        logger.error('Empty playlist: %s', filename)

    tracks = []
    for line in contents.split('\n'):
        matches = match(options['regex'], line)
        logger.debug('%s', matches)
        if matches:
            artist = matches.get('artist')
            album = matches.get('album')
            track = matches.get('track')
            tracks.append([artist, album, track])
    pc.make_playlist(playlist_name, playlist_description, tracks)


def main(options, args):
    logger.debug('Options: %s', options)
    pc = PlaylistCreator()
    if not pc.authenticated:
        logger.error('You need to authenticate by running ./authenticate.py first')
        sys.exit(0)

    for arg in args:
        process_txt(pc, options, arg)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option(
      "-r", "--regex", dest="regex",
      help="regex to match per line", default=r'(?P<artist>.*)\t(?P<album>.*)\t(?P<track>.*)'
    )
    parser.add_option("-d", "--description", dest="description", help="The description for the playlist", default=None)
    (options, args) = parser.parse_args()
    options = options.__dict__
    main(options, args)
