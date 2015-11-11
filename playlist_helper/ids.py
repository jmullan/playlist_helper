#!/usr/bin/env python -S
import logging
import sys
from optparse import OptionParser

from playlistcreator import PlaylistCreator

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def process_txt(pc, options, track_ids):
    playlist_name = options.get('playlist_name')
    playlist_description = options.get('description')
    if playlist_description is None:
        playlist_description = 'Songs about %s' % playlist_name

    track_keys = ['t%s' % track_id for track_id in track_ids]

    pc.make_playlist(playlist_name, playlist_description, track_keys)


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
    parser.add_option("-n", "--name", dest="playlist_name", help="A name for your playlist")
    parser.add_option("-d", "--description", dest="description", help="The description for the playlist", default=None)
    (options, track_ids) = parser.parse_args()
    options = options.__dict__
    main(options, track_ids)
