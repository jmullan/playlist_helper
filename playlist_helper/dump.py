#!/usr/bin/env python
import json
import logging
import pprint
import os
import sys
from optparse import OptionParser

from playlistcreator import PlaylistCreator

logging.basicConfig()
logger = logging.getLogger(__name__)


def convert_track(track):
  if 'album' not in track:
    pprint.pprint(track)

  return {
    "title": track['name'],
    "creator": track['artist'],
    # "annotation": "Some text"
    # "info": "http://example.com/",
    # "image": "http://example.com/",
    "album": track['album'],
    "trackNum": track['trackNum'],
    "duration": (track['duration'] or 0) * 1000,
    'meta': [
      {key: value} for key, value in track.items()
    ]
  }


def dump_playlist(user, playlist):
  jspf_structure = {
    "playlist": {
      "title": playlist['name'],
      "annotation": playlist.get('description', ''),
      "creator": playlist['owner'],
      "track": [
        convert_track(track) for track in playlist['tracks']
      ],
      'meta': [
        {key: value} for key, value in playlist.items()
        if key not in ['tracks']
      ]
    }
  }
  playlist_filename = 'dumps/%s/%s.jspf' % (user['username'], playlist['url'].split('/')[-2])
  print 'dumping %s to %s' % (playlist['name'], playlist_filename)
  with open(playlist_filename, 'w') as outfile:
    json.dump(jspf_structure, outfile, indent=2)


def main(options, args):
  logger.debug('Options: %s', options)
  pc = PlaylistCreator()
  if not pc.authenticated:
    logger.error('You need to authenticate by running `python playlist_helper/authenticate.py` first')
    sys.exit(1)

  user = pc.get_user(username=options['username'], email=options['email'])
  if user is None:
    print 'No user found for %s %s' % (options['username'], options['email'])
    exit(1)
  try:
    os.makedirs('dumps/%s' % user['username'])
  except OSError:
    pass

  for playlist in pc.list_playlists(user):
    dump_playlist(user, playlist)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option(
      "-u", "--username", dest="username", default=None,
      help="dump for USERNAME", metavar="USERNAME"
    )
    parser.add_option(
      "-e", "--email", dest="email", default=None,
      help="dump for EMAIL", metavar="EMAIL"
    )
    (options, args) = parser.parse_args()
    options = options.__dict__
    main(options, args)
