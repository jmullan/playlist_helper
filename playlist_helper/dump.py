#!/usr/bin/env python
import codecs
import csv
import json
import logging
import pprint
import re
import os
import string
import sys
import urllib
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


def makedirs(path):
  try:
    os.makedirs(path)
  except OSError:
   pass


def playlist_slug(playlist_url):
  # /people/leetbmc/playlists/1765046/New_Stuff_to_Listen_To/
  matches = re.search(r'playlists/[^/]+/(.*)/', playlist_url)
  if matches:
    playlist_url = matches.group(1)
  else:
    print 'FIXME' * 100
    print 'Cannot parse url'
    print playlist_url
    exit(1)
  playlist_name = urllib.unquote(playlist_url)
  # playlist_name = playlist_name.decode('utf8', 'ignore')
  safe_characters = string.letters + string.digits + ' -_.'
  return ''.join(c for c in playlist_name if c in safe_characters)


def dump_playlist(user, playlist):
  if not playlist['tracks']:
    print 'No tracks for %s' % playlist['name']
    return

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
  playlist_folder = '%s/' % playlist['playlist_type']
  playlist_folder = 'dumps/%s/playlists/%s' % (user['username'], playlist_folder)
  makedirs(playlist_folder)

  playlist_filename = '%s%s.jspf' % (playlist_folder, playlist_slug(playlist['url']))
  print 'dumping %s to %s' % (playlist['name'], playlist_filename)
  with open(playlist_filename, 'w') as outfile:
    json.dump(jspf_structure, outfile, indent=2)

  playlist_filename = '%s%s.csv' % (playlist_folder, playlist_slug(playlist['url']))
  with open(playlist_filename, 'w') as outfile:
    csv_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for track in playlist['tracks']:
      track = [track[key].encode('utf8', 'ignore') for key in ['artist', 'album', 'name']]
      csv_writer.writerow(track)


def dump_comments(user, comment_data):
  comments_filename = 'dumps/%s/comments.txt' % user['username']
  with codecs.open(comments_filename, 'w', 'utf-8') as outfile:
    for comment in comment_data['comments']:
      commentedItem = comment['commentedItem']
      commentedType = commentedItem['type']

      outfile.write('Comment on "%s"' % commentedItem['name'])
      if commentedType == 'a' or commentedType == 't':
        outfile.write(' by %s' % commentedItem['artist'])
      elif commentedType == 'p':
        outfile.write(' by %s' % commentedItem['owner'])
      outfile.write('\n')

      outfile.write(comment['comment'])
      outfile.write('\n')
      outfile.write('posted on %s\n' % comment['datePosted'])

      likeNames = [like['username'] for like in comment['likes']]
      if likeNames:
          outfile.write('liked by %s\n' % ', '.join(likeNames))

      for reply in comment['replies']:
        outfile.write('\t%s: %s\n' % (reply['commenter']['username'], reply['comment']))
      outfile.write('-' * 92)
      outfile.write('\n')


def dump_iterable(user, name, items):
  items = list(items)
  structure = {name: items}
  filename = 'dumps/%s/%s.json' % (user['username'], name)
  with open(filename, 'w') as outfile:
    json.dump(structure, outfile, indent=2)

  filename = 'dumps/%s/%s.csv' % (user['username'], name)
  with open(filename, 'w') as outfile:
    csv_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for item in items:
      item = item.encode('utf8', 'ignore')
      csv_writer.writerow([item])


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

  makedirs('dumps/%s' % user['username'])
  dump_comments(user, pc.list_comments(user))
  dump_iterable(user, 'favorite_artists', pc.get_favorite_artists(user))
  dump_iterable(user, 'favorite_labels', pc.get_favorite_labels(user))
  dump_iterable(user, 'favorite_stations', pc.get_favorite_stations(user))
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
