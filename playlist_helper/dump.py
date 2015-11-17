#!/usr/bin/env python
import logging
import pprint
import os
import sys
from optparse import OptionParser

from playlistcreator import PlaylistCreator

logging.basicConfig()
logger = logging.getLogger(__name__)


def convert_track(track):
  sample_track = {
    u'album': u'Main Title Song (From "Big Trouble in Little China") (Single)',
    u'albumArtist': u'Dh Music',
    u'albumArtistKey': u'r3551091',
    u'albumKey': u'a4006039',
    u'albumUrl': u'/artist/Dh_Music/album/Main_Title_Song_(From_%22Big_Trouble_in_Little_China%22)_(Single)/',
    u'artist': u'Dh Music',
    u'artistKey': u'r3551091',
    u'artistUrl': u'/artist/Dh_Music/',
    u'baseIcon': u'album/7/9/0/00000000003d2097/1/square-200.jpg',
    u'canDownload': False,
    u'canDownloadAlbumOnly': False,
    u'canSample': True,
    u'canStream': True,
    u'canTether': True,
    u'duration': 195,
    u'dynamicIcon': u'http://rdiodynimages0-a.akamaihd.net/?l=a4006039-1',
    u'embedUrl': u'https://rd.io/e/QB84K0HTzxA/',
    u'gridIcon': u'http://rdiodynimages1-a.akamaihd.net/?l=a4006039-1%3Aboxblur%2810%25%2C10%25%29%3Ba4006039-1%3Aprimary%280.65%29%3B%240%3Aoverlay%28%241%29%3Ba4006039-1%3Apad%2850%25%29%3B%242%3Aoverlay%28%243%29',
    u'icon': u'http://rdio3img-a.akamaihd.net/album/7/9/0/00000000003d2097/1/square-200.jpg',
    u'icon400': u'http://rdio1img-a.akamaihd.net/album/7/9/0/00000000003d2097/1/square-400.jpg',
    u'isClean': False,
    u'isExplicit': False,
    u'key': u't42769745',
    u'length': 1,
    u'name': u'Main Title Song (From "Big Trouble in Little China") (Single)',
    u'price': None,
    u'radio': {u'key': u'sr42769745', u'type': u'sr'},
    u'radioKey': u'sr42769745',
    u'shortUrl': u'http://rd.io/x/QB84K0HTzxA/',
    u'trackNum': 1,
    u'type': u't',
    u'url': u'/artist/Dh_Music/album/Main_Title_Song_'
  }

  return {
    "title": track['name'],
    "creator": track['artist'],
    # "annotation": "Some text"
    # "info": "http://example.com/",
    # "image": "http://example.com/",
    "album": track['album'],
    "trackNum": track['trackNum'],
    "duration": track['duration'] * 1000,
    'meta': [
      {key: value} for key, value in track.items()
    ]
  }


def dump_playlist(playlist):

  sample_structure = {
    u'ownerKey': u's16506',
    u'name': u'Purple Covers',
    u'shortUrl': u'http://rd.io/x/QB84L5Hhbw/',
    u'baseIcon': u'album/3/a/a/0000000000016aa3/1/square-200.jpg',
    u'ownerIcon': u'user/a/7/0/000000000000407a/1/square-100.jpg',
    u'owner': u'Jesse Mullan',
    u'lastUpdated': 1440834342.0,
    u'url': u'/people/jmullan/playlists/13811261/Purple_Covers/',
    u'length': 7,
    u'key': u'p13811261',
    u'ownerUrl': u'/people/jmullan/',
    u'embedUrl': u'https://rd.io/e/QB84L5Hhbw/',
    u'icon': u'http://img00.cdn2-rdio.com/playlist/d/3/e/0000000000d2be3d/1/square-200.jpg',
    u'type': u'p',
    u'dynamicIcon': u'http://rdiodynimages1-a.akamaihd.net/?l=p13811261-1'
  }

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
  pprint.pprint(jspf_structure)


def main(options, args):
  logger.debug('Options: %s', options)
  pc = PlaylistCreator()
  if not pc.authenticated:
    logger.error('You need to authenticate by running `python playlist_helper/authenticate.py` first')
    sys.exit(1)

  playlists = pc.list_playlists()
  if playlists:
    try:
      os.mkdir('dumps')
    except OSError:
      pass

  for playlist in playlists:
    dump_playlist(playlist)


if __name__ == "__main__":
    parser = OptionParser()
    (options, args) = parser.parse_args()
    options = options.__dict__
    main(options, args)
