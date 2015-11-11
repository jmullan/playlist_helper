#!/usr/bin/env python
import codecs
import json
import logging
import os
import subprocess
import sys
from optparse import OptionParser

from playlistcreator import PlaylistCreator

sample = """
#CURTRACK 67
#EXTM3U
#EXTURL:file:///mnt/space/music/Picarded/Jennifer%20Lopez%20feat.%20Iggy%20Azalea/Booty/01%20Booty.mp3
#EXTINF:209,Booty
/mnt/space/music/Picarded/Jennifer Lopez feat. Iggy Azalea/Booty/01 Booty.mp3
#EXTURL:file:///mnt/space/music/Picarded/Dr.%20Octagon/Dr.%20Octagon,%20Part%20II/12%20Can%20I%20Touch%20Ya%20Butt%20Girl_.mp3
#EXTINF:226,Can I Touch Ya Butt Girl?
/mnt/space/music/Picarded/Dr. Octagon/Dr. Octagon, Part II/12 Can I Touch Ya Butt Girl_.mp3
#EXTURL:file:///mnt/space/music/Picarded/Infectious%20Grooves/Sarsippius%27%20Ark/19%20Big%20Big%20Butt,%20by%20Infectiphibian.mp3
#EXTINF:55,Big Big Butt, by Infectiphibian
/mnt/space/music/Picarded/Infectious Grooves/Sarsippius' Ark/19 Big Big Butt, by Infectiphibian.mp3
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


def process_m3u(pc, filename):
    if not os.path.isfile(filename):
        logger.error('Not a file: %s', filename)
        return

    playlist_name = os.path.splitext(os.path.basename(filename))[0]
    playlist_description = 'Songs about %s' % playlist_name

    contents = ''
    filesize = os.path.getsize(filename)
    with open(filename) as f:
        contents = f.read(filesize)
    if not contents:
        logger.error('Empty playlist: %s', filename)

    tracks = []
    for line in contents.split('\n'):
        music_file_path = None
        track_info = None
        if line.startswith(codecs.BOM_UTF8):
            line = line[3:]
        line = line.strip()
        if not line.startswith('#'):
            music_file_path = line
        if not music_file_path:
            continue
        command = ['exiftool', '-json', music_file_path]
        track_json = subprocess.Popen(command, stdout=subprocess.PIPE).stdout.read()
        try:
            track_info = json.loads(track_json)
        except ValueError:
            logger.error('Could not load id3 data from %s', music_file_path)
            track_info = None
        if not track_info:
            logger.error('Could not load track info for %s', music_file_path)
            continue
        track = [track_info[0]['Artist'], track_info[0]['Title']]
        tracks.append(track)
    pc.make_playlist(playlist_name, playlist_description, tracks)


def main(options, args):
    logger.debug('Options: %s', options)
    pc = PlaylistCreator()
    if not pc.authenticated:
        logger.error('You need to authenticate by running ./authenticate.py first')
        sys.exit(0)

    for arg in args:
        process_m3u(pc, arg)


if __name__ == "__main__":

    parser = OptionParser()
    (options, args) = parser.parse_args()
    options = options.__dict__
    main(options, args)
