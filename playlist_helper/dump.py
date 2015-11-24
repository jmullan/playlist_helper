#!/usr/bin/env python
"""Dumps your rdio data."""
import codecs
import csv
import json
import logging
import os
import pprint
import re
import string
import sys
import urllib
from optparse import OptionParser

from contrib import xspf
from playlistcreator import PlaylistCreator

logging.basicConfig()
logger = logging.getLogger(__name__)


def convert_track(track):
    """Turn a requested track into something for jspf."""
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
          {_meta('t/%s' % key): unicode(value)} for key, value in track.items()
      ]
    }


def xspf_track(track):
    """Instantiate and xspf.Track based on rdio data."""
    t = convert_track(track)
    meta = t['meta']
    del t['meta']
    t['trackNum'] = '%d' % t['trackNum']
    t['duration'] = '%d' % t['duration']
    x = xspf.Track(t)
    for items in meta:
        for key, value in items.items():
            x.add_meta(key, value)
    return x


def makedirs(path):
    """Wrap os.makedirs to behave like `mkdir -p`."""
    try:
        os.makedirs(path)
    except OSError:
        pass


def playlist_slug(playlist):
    """Turn a playlist URL into a file basename."""
    # /people/leetbmc/playlists/1765046/New_Stuff_to_Listen_To/
    playlist_url = playlist['url']
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
    playlist_name = ''.join(c for c in playlist_name if c in safe_characters)
    playlist_name = re.sub('_+', '_', playlist_name)
    return playlist_name


def _meta(key):
    """Make an arbitrary url for xspf meta fields."""
    return 'https://rdio.com/xspf/%s' % urllib.quote(key)


def dump_playlist(user, playlist):
    """Given a user and playlist, dump that playlist into csv and jspf files."""
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
            {_meta('p/%s' % key): unicode(value)} for key, value in playlist.items()
            if key not in ['tracks']
        ]
      }
    }
    playlist_folder = '%s/' % playlist['playlist_type']
    playlist_folder = 'dumps/%s/playlists/%s' % (user['username'], playlist_folder)
    makedirs(playlist_folder)

    x = xspf.Xspf()
    x.title = playlist['name']
    x.annotation = playlist.get('description', '')
    x.creator = playlist['owner']
    for key, value in playlist.items():
        if key not in ['tracks']:
            x.add_meta(_meta(key), unicode(value))

    for track in playlist['tracks']:
        xtrack = xspf_track(track)
        x.add_track(xtrack)

    playlist_name = playlist_slug(playlist)
    if not playlist_name or playlist_name in user['_playlists']:
        playlist_name = '%s__%s' % (playlist['key'], playlist_name)

    user['_playlists'].add(playlist_name)

    if not playlist_name:
        print 'Could not generate playlist name for:'
        pprint.pprint(playlist)
        exit(1)

    playlist_filename = '%s%s.xspf' % (playlist_folder, playlist_name)
    with codecs.open(playlist_filename, 'w', 'utf-8', 'ignore') as outfile:
        xml = x.toXml().decode('utf-8', errors='ignore')
        outfile.write(xml)

    playlist_filename = '%s%s.jspf' % (playlist_folder, playlist_name)
    with codecs.open(playlist_filename, 'w', 'utf-8', 'ignore') as outfile:
        json.dump(jspf_structure, outfile, indent=2)

    playlist_filename = '%s%s.csv' % (playlist_folder, playlist_name)
    with codecs.open(playlist_filename, 'w', 'utf-8', 'ignore') as outfile:
        csv_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for track in playlist['tracks']:
            track = [track[key].encode('ascii', 'ignore') for key in ['artist', 'album', 'name']]
            try:
                csv_writer.writerow(track)
            except Exception:
                print track
                raise

    playlist_filename = '%s%s.m3u' % (playlist_folder, playlist_name)
    with codecs.open(playlist_filename, 'w', 'cp1252', 'ignore') as outfile:
        # m3u files are supposed to be cp1252: https://en.wikipedia.org/wiki/M3U
        outfile.write('#EXTM3U\n')
        for track in playlist['tracks']:
            outfile.write('#EXTINF:%s,%s - %s\n' % ((track['duration'] or 0) * 1000, track['artist'], track['name']))
            outfile.write('%s/%s/%s - %s.mp3\n' % (track['artist'], track['album'], track['trackNum'], track['name']))


def simplify_comment(comment):
    """Drop extraneous comment information and package it into a nicer structure."""
    commentedItem = comment['commentedItem']
    commentedType = commentedItem['type']
    if commentedType in ['a', 't']:
        commentedItemBy = commentedItem['artist']
    elif commentedType == 'p':
        commentedItemBy = commentedItem['owner']
    else:
        commentedItemBy = None

    return {
        'comment': comment['comment'],
        'on_item': {
            'name': commentedItem['name'],
            'by': commentedItemBy,
        },
        'posted': comment['datePosted'],
        'likes': [like['username'] for like in comment['likes']],
        'replies': [
            (reply['commenter']['username'], reply['comment'])
            for reply in comment['replies']
        ]
    }


def dump_comments(user, comment_data):
    """Given a comments data structure, make a json and readable file."""
    json_structure = {
        'comments': [
            simplify_comment(comment)
            for comment in comment_data['comments']
            if comment['commentedItem'] is not None
        ]
    }

    comments_filename = 'dumps/%s/comments.json' % user['username']
    with codecs.open(comments_filename, 'w', 'utf-8') as outfile:
        json.dump(json_structure, outfile, indent=2)

    comments_filename = 'dumps/%s/comments.txt' % user['username']
    with codecs.open(comments_filename, 'w', 'utf-8') as outfile:
        for comment in comment_data['comments']:
            commentedItem = comment['commentedItem']
            if commentedItem is None:
                commentedType = '??????'
                commentedOnName = 'a missing item.'
            else:
                commentedType = commentedItem['type']
                commentedOnName = commentedItem['name']

            outfile.write('Comment on "%s"' % commentedOnName)
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
    """Write an iterable to a csv and json file."""
    items = list(items)
    structure = {name: items}
    filename = 'dumps/%s/%s.json' % (user['username'], name)
    with codecs.open(filename, 'w', 'utf-8') as outfile:
        json.dump(structure, outfile, indent=2)

    filename = 'dumps/%s/%s.csv' % (user['username'], name)
    with codecs.open(filename, 'w', 'utf-8') as outfile:
        csv_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for item in items:
            item = item.encode('utf8', 'ignore')
            csv_writer.writerow([item])


def main(options, args):
    """Run all the things."""
    pc = PlaylistCreator()
    if not pc.authenticated:
        logger.error('You need to authenticate by running `python playlist_helper/authenticate.py` first')
        sys.exit(1)

    user = pc.get_user(
        username=options['username'],
        email=options['email'],
        uid_key=options['uid_key']
    )
    if user is None:
        print 'No user found for %s %s' % (options['username'], options['email'])
        exit(1)
    makedirs('dumps/%s' % user['username'])
    dump_comments(user, pc.list_comments(user))
    dump_iterable(user, 'favorite_artists', pc.get_favorite_artists(user))
    dump_iterable(user, 'favorite_labels', pc.get_favorite_labels(user))
    dump_iterable(user, 'favorite_stations', pc.get_favorite_stations(user))

    user['_playlists'] = set()
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
    parser.add_option(
      "--uid", dest="uid_key", default=None,
      help="dump for UID or key", metavar="UID"
    )
    (options, args) = parser.parse_args()
    options = options.__dict__
    main(options, args)
