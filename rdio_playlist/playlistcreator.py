"""
A Python class for creating and updating playlists based on track and artist
names
"""

import ConfigParser
import os.path
import shelve
import logging
import json
import re
from rdioapi import Rdio

_PATH = os.path.dirname(os.path.realpath(__file__))

def uniq(seq):
  """return non-duplicate items from a sequence, in order"""
  u = []
  for i in seq:
    if i not in u: u.append(i)
  return u

LOGGER = logging.getLogger(__name__)


class Fuzzy(unicode):
  """
  A string where equality is defined as: edit distance as a percentage of
  the sum of the lengths of the inputs <= 25%
  """
  def __eq__(self, other):
    from levenshtein_distance import levenshtein_distance as distance
    d = distance(self.lower(), other.lower())
    denominator = float(len(self + other))
    if denominator == 0:
      return False
    return int(100 * float(d) / denominator) <= 25


class Term(unicode):
  """A string that knows about fuzzy matching and simple transforms"""

  PAREN_RE = re.compile(r'\([^)]*\)') # remove text in parens
  FEATURE_RE = re.compile(r' (&|Feat\.|feat\.|Featuring|featuring) .*') # remove & / Feat. / feat.
  TRACK_NUM_RE = re.compile(r'^[0-9]+ ')

  @property
  def forms(self):
    return (
      self,
      Term.PAREN_RE.sub('', self),
      Term.FEATURE_RE.sub('', self),
      self.replace('!', ' '), # for Wakey Wakey!
    )

  def __eq__(self, other):
    fuzz = Fuzzy(other)
    return any((fuzz == f for f in self.forms))


class PlaylistCreator(object):

  def __init__(self):
    self._config = None
    self._client_id = None
    self._client_secret = None
    self._client_callback_uri = None
    self.oauth_state = shelve.open('oauth_state')
    self.found_tracks = shelve.open('found_tracks')

  def __del__(self):
    self.oauth_state.close()
    self.found_tracks.close()

  @property
  def config(self):
    if self._config is None:
      self._config = ConfigParser.ConfigParser()
      path = _PATH + '/../client.ini'
      self._config.read([path, os.path.expanduser('~/.rdio-client.ini')])
    return self._config

  @property
  def client_id(self):
    if self._client_id is None:
      self._client_id = self.config.get('oauth', 'client_id')
    return self._client_id

  @property
  def client_secret(self):
    if self._client_secret is None:
      self._client_secret = self.config.get('oauth', 'client_secret')
    return self._client_secret

  __cached_rdio = None
  @property
  def rdio(self):
    if self.__cached_rdio is None:
      self.__cached_rdio = Rdio(
        self.client_id, self.client_secret, self.oauth_state)
    return self.__cached_rdio

  @property
  def authenticated(self):
    if not self.rdio.authenticated:
      return False
    try:
      return self.rdio.currentUser() is not None
    except BaseException as ex:
      print ex
      raise
      return False
      self.rdio.logout()
      return False

  def authenticate(self):
    # let's clear our old auth state
    for k in self.oauth_state.keys():
      del self.oauth_state[k]
    self.__cached_rdio = None

    # do a PIN based auth
    import webbrowser
    url, device_code = self.rdio.begin_authentication()
    print 'Please enter device code: %s on %s' % (device_code, url)
    webbrowser.open(url)
    self.rdio.complete_authentication()
    print 'Successfully authenticated'

  def find_album_track(self, artist, album, title):
    """try to find a track but apply various transfomations"""
    if album is None or album == '':
      return self.find_track(artist, title)

    artist = Term(artist)
    album = Term(album)
    title = Term(title)


    # for each of the forms, search...
    for a, r, t in uniq(zip(artist.forms, album.forms, title.forms)):
      # query the API
      q = ('%s %s %s' % (a, r, t)).encode('utf-8')
      result = self.rdio.search(query=q, types='Track', never_or=True)

      # if there were no results then the search failed
      if not result['track_count']:
        LOGGER.warning('rdio.search failed for: "%s"', q)
        continue

      # look through the results for a good match
      for track in result['results']:
        if artist == track['artist'] and title == track['name'] and (album is None or album == track['album']):
          return track
      # none found
      LOGGER.warning('rdio.search succeeded but match failed for "%s"', q)
      return None

  def find_track(self, artist, title):
    """try to find a track but apply various transfomations"""
    artist = Term(artist)
    title = Term(title)

    # for each of the forms, search...
    for a, t in uniq(zip(artist.forms, title.forms)):
      # query the API
      q = ('%s %s' % (a, t)).encode('utf-8')
      result = self.rdio.search(query=q, types='Track', never_or=True)

      # if there were no results then the search failed
      if not result['track_count']:
        LOGGER.warning('rdio.search failed for: %s', q)
        continue

      # look through the results for a good match
      for track in result['results']:
        if artist == track['artist'] and title == track['name']:
          return track
      # none found
      LOGGER.warning('rdio.search succeeded but match failed: "%s"', q)
      return None

  def make_playlist(self, name, desc, tracks):
    """make or update a playlist named @name, with a description @desc, with the tracks specified in @tracks, a list of (artistname, trackname) pairs"""
    tracks_meta = []
    if not tracks:
      LOGGER.warn('No tracks for playlist')
      return

    for track in tracks:
      if len(track) == 2:
        albumname = None
        artistname, trackname = track
        key = json.dumps((artistname, trackname)).encode('utf-8')
        LOGGER.debug('Looking for: %s' % key)
      elif len(track) == 3:
        artistname, albumname, trackname = track
        key = json.dumps((artistname, albumname, trackname)).encode('utf-8')

      if key in self.found_tracks:
        LOGGER.info(' found it in the cache: %s' % self.found_tracks[key]['key'])
        tracks_meta.append(self.found_tracks[key])
      else:
        track_meta = None
        if albumname is not None:
          track_meta = self.find_album_track(artistname, albumname, trackname)
        if track_meta is None:
          track_meta = self.find_track(artistname, trackname)
        if track_meta is not None:
          LOGGER.info(' found it in on the site: %s' % track_meta['key'])
          tracks_meta.append(track_meta)
          self.found_tracks[key] = track_meta
        else:
          LOGGER.info(' not found')
          pass

    LOGGER.info('Found %d / %d tracks' % (len(tracks_meta), len(tracks)))

    track_keys = [track['key'] for track in tracks_meta]

    unique_track_keys = set()
    ordered_unique_track_keys = []
    for track_key in track_keys:
      if track_key not in unique_track_keys:
        unique_track_keys.add(track_key)
        ordered_unique_track_keys.append(track_key)

    # ask the server for playlists
    playlists = self.rdio.getPlaylists()
    for playlist in playlists['owned']:
      # look for a playlist with the right name
      if playlist['name'] == name:
        LOGGER.info('Found the playlist')
        # when we find it, remove all of those tracks...
        playlist = self.rdio.get(keys=playlist['key'], extras='tracks')[playlist['key']]
        playlist_keys = set([t['key'] for t in playlist['tracks']])
        remove_keys = playlist_keys - unique_track_keys
        if remove_keys:
          self.rdio.removeFromPlaylist(playlist=playlist['key'],
                                       index=0, count=playlist['length'],
                                       tracks=','.join(remove_keys))
        # now add all of the tracks we just got
        add_keys = unique_track_keys - playlist_keys
        if add_keys:
          self.rdio.addToPlaylist(playlist=playlist['key'], tracks=','.join(add_keys))
        LOGGER.info('Updated the playlist')
        break
    else:
      # didn't find the playlist
      # create it!
      playlist = self.rdio.createPlaylist(name=name,
                                          description=desc,
                                          tracks=','.join(ordered_unique_track_keys))
      LOGGER.info('Created the playlist')
