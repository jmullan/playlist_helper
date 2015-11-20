"""A Python class for creating and updating playlists based on track and artist names."""

import ConfigParser
import json
import logging
import os.path
import re
import shelve
import sys

from levenshtein_distance import levenshtein_distance as distance
from rdioapi import Rdio

_PATH = os.path.dirname(os.path.realpath(__file__))

LOGGER = logging.getLogger(__name__)


def best_unicode(unknown_string):
    if isinstance(unknown_string, unicode):
        return unknown_string

    unknown_string = unknown_string.decode('UTF-8')
    return unknown_string


def uniq(seq):
    """return non-duplicate items from a sequence, in order"""
    u = []
    for i in seq:
        if i not in u:
            u.append(i)
    return u


def fuzz(term, other):
    d = distance(term.lower(), other.lower())
    denominator = float(len(term + other))
    if denominator == 0:
        return False
    return int(100 * float(d) / denominator) <= 25


class Term(unicode):
    """A string that knows about fuzzy matching and simple transforms."""

    PAREN_RE = re.compile(r' *\([^)]*\)') # remove text in parens
    FEATURE_RE = re.compile(r' (&|Feat\.|feat\.|Featuring|featuring) .*') # remove & / Feat. / feat.
    TRACK_NUM_RE = re.compile(r'^[0-9]+ ')
    THE_RE = re.compile(r'^The, (.*)')
    RE_THE = re.compile(r'(.*), The$')

    @property
    def forms(self):
        return set((
          '%s' % self,
          Term.PAREN_RE.sub('', self),
          Term.FEATURE_RE.sub('', self),
          self.replace('!', ' '),
          self.replace(' and ', ' & '),
          self.replace(' & ', ' and '),
          re.sub(Term.THE_RE, '\1, The', self),
          re.sub(Term.RE_THE, 'The \1', self),
          re.sub(Term.THE_RE, '\1', self),
          re.sub(Term.RE_THE, '\1', self),
        ))

    def __eq__(self, other):
        if not isinstance(other, Term):
            other = Term(other)
        for f in self.forms:
            for g in other.forms:
                if fuzz(f, g):
                    return True
        return False


class PlaylistCreator(object):
    _cached_rdio = None

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

    @property
    def rdio(self):
        if self._cached_rdio is None:
            self._cached_rdio = Rdio(
              self.client_id, self.client_secret, self.oauth_state)
        return self._cached_rdio

    @property
    def authenticated(self):
        if not self.rdio.authenticated:
            return False
        try:
            return self.rdio.currentUser() is not None
        except BaseException as ex:
            print ex
            self.rdio.logout()
            return False

    def authenticate(self):
        # let's clear our old auth state
        for k in self.oauth_state.keys():
            del self.oauth_state[k]
        self._cached_rdio = None

        # do a PIN based auth
        import webbrowser
        url, device_code = self.rdio.begin_authentication()
        print 'Please enter device code: %s on %s' % (device_code, url)
        webbrowser.open(url)
        self.rdio.complete_authentication()
        print 'Successfully authenticated'

    def find_artist_tracks(self, artist):
        """try to find a track but apply various transfomations."""
        artist = Term(artist)
        LOGGER.info('Finding tracks for artist %s', artist)
        search_succeeded = False

        # for each of the forms, search...
        album_keys = []
        for a in uniq(artist.forms):
            # query the API
            q = ('%s' % a).encode('utf-8')
            result = self.rdio.search(query=q, types='Artist', never_or=True, extras="albumKeys")

            # if there were no results then the search failed
            if not result or not result.get('artist_count'):
                LOGGER.warning('rdio.search failed for: "%s"', q)
                continue

            # look through the results for a good match
            search_succeeded = True
            for artist_result in result['results']:
                if artist == artist_result['name']:
                    if not artist_result.get('albumKeys'):
                        LOGGER.warn('No track keys for album result: %r', artist_result)
                    album_keys = artist_result.get('albumKeys')
                    break

        track_keys = []
        for album_key in album_keys:
            albums = self.rdio.get(keys=','.join(album_keys))
            for album in albums.values():
                album_tracks = album.get('trackKeys', [])
                track_keys += album_tracks
        track_keys = uniq(track_keys)

        if search_succeeded:
            if not track_keys:
                LOGGER.warning('rdio.search succeeded but match failed for: %s', artist)
                LOGGER.warning('No tracks found for artist: %s', artist)
        else:
            LOGGER.warning('rdio.search completely failed for: %s', artist)
        return track_keys

    def find_album_tracks(self, artist, album):
        """try to find a track but apply various transfomations."""
        if album is None or album == '':
            LOGGER.warn('No album given for artist: %s %s', artist, album)
            return []

        artist = Term(artist)
        album = Term(album)

        LOGGER.info('Finding tracks for artist %s album %s', artist, album)
        search_succeeded = False

        # for each of the forms, search...
        for a, r in uniq(zip(artist.forms, album.forms)):
            # query the API
            q = ('%s %s' % (a, r)).encode('utf-8')
            result = self.rdio.search(query=q, types='Album', never_or=True)

            # if there were no results then the search failed
            if not result['album_count']:
                LOGGER.warning('rdio.search failed for: "%s"', q)
                continue

            # look through the results for a good match
            search_succeeded = True
            for album_result in result['results']:
                if artist == album_result['artist'] and album == album_result['name']:
                    if not album_result['trackKeys']:
                        LOGGER.warn('No track keys for album result: %r', album_result)
                    return album_result['trackKeys']

        if album == artist:
            # query the API
            q = ('%s' % a).encode('utf-8')
            result = self.rdio.search(query=q, types='Album', never_or=True)

            # if there were no results then the search failed
            if not result['album_count']:
                LOGGER.warning('rdio.search failed for: "%s"', q)
            else:
                # look through the results for a good match
                search_succeeded = True
                for album_result in result['results']:
                    if artist == album_result['artist'] and album == album_result['name']:
                        if not album_result['trackKeys']:
                            LOGGER.warn('No track keys for album result: %r', album_result)
                        return album_result['trackKeys']
        # none found
        if search_succeeded:
            LOGGER.warning('rdio.search succeeded but match failed for: %s %s', artist, album)
        else:
            LOGGER.warning('rdio.search completely failed for: %s %s', artist, album)
        return []

    def find_album_track(self, artist, album, title):
        """try to find a track but apply various transfomations."""
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
        """try to find a track but apply various transfomations."""
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

    def get_artists_meta(self, tracks):
        tracks_meta = []
        for track in tracks:
            artistname, albumname, _ = track
            track_meta = self.find_artist_tracks(artistname)
            for track in track_meta:
                tracks_meta.append({'key': track})
        return tracks_meta

    def get_albums_meta(self, tracks):
        tracks_meta = []
        for track in tracks:
            artistname, albumname, _ = track
            track_meta = self.find_album_tracks(artistname, albumname)
            for track in track_meta:
                tracks_meta.append({'key': track})
        return tracks_meta

    def get_tracks_meta(self, tracks):
        tracks_meta = []
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
                LOGGER.info('found it in the cache: %s' % self.found_tracks[key]['key'])
                tracks_meta.append(self.found_tracks[key])
            else:
                track_meta = None
                if albumname is not None:
                    track_meta = self.find_album_track(artistname, albumname, trackname)
                if track_meta is None:
                    track_meta = self.find_track(artistname, trackname)
                if track_meta is not None:
                    LOGGER.info('found it in on the site: %s' % track_meta['key'])
                    tracks_meta.append(track_meta)
                    self.found_tracks[key] = track_meta
                else:
                    LOGGER.info('not found')
                    pass
        return tracks_meta

    def make_playlist(self, name, desc, tracks):
        """Make or update a playlist.

        named @name, with a description @desc
        with the tracks specified in @tracks, a list of (artistname, [albumname], trackname) pairs
        """
        if not tracks:
            LOGGER.warn('No tracks for playlist')
            return

        if all((len(track) == 3) and (not track[1]) and (not track[2]) for track in tracks):
            tracks_meta = self.get_artists_meta(tracks)
        elif all((len(track) == 3) and (not track[2]) for track in tracks):
            tracks_meta = self.get_albums_meta(tracks)
        else:
            tracks_meta = self.get_tracks_meta(tracks)

        LOGGER.info('Found %d / %d tracks' % (len(tracks_meta), len(tracks)))
        track_keys = [track['key'] for track in tracks_meta]
        self.make_playlist_from_keys(name, desc, track_keys)

    def make_playlist_from_keys(self, name, desc, track_keys):
        ordered_unique_track_keys = uniq(track_keys)
        unique_track_keys = set(ordered_unique_track_keys)

        if not ordered_unique_track_keys:
            LOGGER.warn('No tracks found')
            return

        name = best_unicode(name)
        desc = best_unicode(desc)

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
            playlist = self.rdio.createPlaylist(name=name.encode('utf-8'),
                                                description=desc.encode('utf-8'),
                                                tracks=','.join(ordered_unique_track_keys))
            LOGGER.info('Created the playlist')

    def get_user(self, username=None, email=None):
        if email is not None:
            current_user = self.rdio.findUser(email=email, extras='vanityName')
        elif username is not None:
            current_user = self.rdio.findUser(vanityName=username, extras='vanityName')
        else:
            current_user = self.rdio.currentUser(extras='vanityName')
        return current_user

    def get_favorites_playlist(self, current_user=None):
        count = 100

        if current_user is None:
            current_user = self.rdio.currentUser()

        current_user_key = current_user['key']
        fullName = '%s %s' % (current_user['firstName'], current_user['lastName'])

        print 'getting favorites'

        favorite_tracks = []
        start = 0

        while True:
            if start:
                print start,
                sys.stdout.flush()
            favorites_response = self.rdio.getFavorites(
              types='tracksAndAlbums',
              extras='tracks,Track.isrcs',
              start=start,
              count=count,
              user=current_user_key
            )
            for item in favorites_response:
                if 'tracks' not in item:
                    favorite_tracks.append(item)
                else:
                    favorite_tracks += item['tracks']
            if len(favorites_response) < count:
                break
            start += len(favorites_response)

        return {
          u'ownerKey': current_user_key,
          u'name': 'Favorites of %s' % fullName,
          # u'shortUrl': u'http://rd.io/x/QB84L5Hhbw/',
          # u'baseIcon': u'album/3/a/a/0000000000016aa3/1/square-200.jpg',
          # u'ownerIcon': u'user/a/7/0/000000000000407a/1/square-100.jpg',
          u'owner': fullName,
          # u'lastUpdated': 1440834342.0,
          u'url': '%s/playlists/%s/favorites/' % (current_user['url'], current_user['key']),
          u'length': len(favorite_tracks),
          # u'key': u'p13811261',
          u'ownerUrl': current_user['url'],
          # u'embedUrl': u'https://rd.io/e/QB84L5Hhbw/',
          # u'icon': u'http://img00.cdn2-rdio.com/playlist/d/3/e/0000000000d2be3d/1/square-200.jpg',
          # u'type': u'p',
          # u'dynamicIcon': u'http://rdiodynimages1-a.akamaihd.net/?l=p13811261-1',
          u'tracks': favorite_tracks,
          u'playlist_type': 'special'
        }

    def get_offline_tracks(self, current_user=None):
        count = 100

        if current_user is None:
            current_user = self.rdio.currentUser()

        current_user_key = current_user['key']
        fullName = '%s %s' % (current_user['firstName'], current_user['lastName'])

        print 'getting downloaded / offline'
        favorite_tracks = []
        start = 0

        while True:
            if start:
                print start,
                sys.stdout.flush()
            favorites_response = self.rdio.getSynced(
              types='tracksAndAlbums',
              extras='tracks,Track.isrcs',
              start=start,
              count=count,
              user=current_user_key
            )
            for item in favorites_response:
                if 'tracks' not in item:
                    favorite_tracks.append(item)
                else:
                    favorite_tracks += item['tracks']
            if len(favorites_response) < count:
                break
            start += len(favorites_response)

        return {
          u'ownerKey': current_user_key,
          u'name': 'Downloaded tracks for %s' % fullName,
          # u'shortUrl': u'http://rd.io/x/QB84L5Hhbw/',
          # u'baseIcon': u'album/3/a/a/0000000000016aa3/1/square-200.jpg',
          # u'ownerIcon': u'user/a/7/0/000000000000407a/1/square-100.jpg',
          u'owner': fullName,
          # u'lastUpdated': 1440834342.0,
          u'url': '%s/playlists/%s/downloaded/' % (current_user['url'], current_user['key']),
          u'length': len(favorite_tracks),
          # u'key': u'p13811261',
          u'ownerUrl': current_user['url'],
          # u'embedUrl': u'https://rd.io/e/QB84L5Hhbw/',
          # u'icon': u'http://img00.cdn2-rdio.com/playlist/d/3/e/0000000000d2be3d/1/square-200.jpg',
          # u'type': u'p',
          # u'dynamicIcon': u'http://rdiodynimages1-a.akamaihd.net/?l=p13811261-1',
          u'tracks': favorite_tracks,
          u'playlist_type': 'special'
        }

    def list_playlists(self, current_user=None):
        count = 100

        if current_user is None:
            current_user = self.rdio.currentUser()
        current_user_key = current_user['key']

        yield self.get_favorites_playlist(current_user)
        yield self.get_offline_tracks(current_user)

        playlist_response = self.rdio.getPlaylists(user=current_user_key)

        urls = set()
        for playlist_type in ['owned', 'collab', 'favorites', 'subscribed']:
            for playlist in playlist_response.get(playlist_type, []):
                if playlist['url'] in urls:
                    print 'Skipping, already processed:', playlist['name']
                    continue
                urls.add(playlist['url'])
                print 'getting', playlist_type, playlist['name']
                playlist['playlist_type'] = playlist_type
                playlist['tracks'] = []
                start = 0
                while True:
                    if start:
                        print start,
                        sys.stdout.flush()
                    playlist_tracks = self.rdio.get(
                      keys=playlist['key'],
                      extras='[{"field":"*.WEB"},{"field":"*","exclude":true},{"field":"tracks","start":%s,"count":%s,"extras":["Track.isrcs"]}]' % (
                        start, count)
                    )[playlist['key']]
                    if len(playlist_tracks['tracks']) < count:
                        break
                    start += len(playlist_tracks['tracks'])
                playlist['tracks'] = playlist_tracks['tracks']
                print 'got', playlist_type, playlist['name']
                yield playlist

    def get_favorite_artists(self, current_user):
        if current_user is None:
            current_user = self.rdio.currentUser()

        current_user_key = current_user['key']

        start = 0
        count = 15
        while True:
            favorites_response = self.rdio.getFavorites(
              types='artists',
              start=start,
              count=count,
              user=current_user_key
            )
            start += len(favorites_response)
            for artist in favorites_response:
                yield artist['name']
            if len(favorites_response) < count:
                break

    def get_favorite_labels(self, current_user):
        if current_user is None:
            current_user = self.rdio.currentUser()

        current_user_key = current_user['key']

        start = 0
        count = 15
        while True:
            favorites_response = self.rdio.getFavorites(
              types='labels',
              start=start,
              count=count,
              user=current_user_key
            )
            start += len(favorites_response)
            for label in favorites_response:
                yield label['name']
            if len(favorites_response) < count:
                break

    def get_favorite_stations(self, current_user):
        if current_user is None:
            current_user = self.rdio.currentUser()

        current_user_key = current_user['key']

        start = 0
        count = 15
        while True:
            favorites_response = self.rdio.getFavorites(
              types='stations',
              start=start,
              count=count,
              user=current_user_key
            )
            start += len(favorites_response)
            for station in favorites_response:
                yield station['name']
            if len(favorites_response) < count:
                break

    def list_comments(self, current_user=None):
        if current_user is None:
            current_user = self.rdio.currentUser()

        current_user_key = current_user['key']
        # Testing with blurbers
        # current_user_key = "s69538"
        # current_user_key = "s3672998"

        comment_data = {
          'comments': []
        }

        print 'getting comments'
        start = 0
        count = 50
        extras_template = '[{"field": "comments", "start": %d, "count": %d, "extras": [{"field": "commentedItem"}, {"field": "likes", "extras": "username"}]}]'
        while True:
            if start:
                print start,
                sys.stdout.flush()
            extras = extras_template % (start, count)
            response = self.rdio.get(keys=current_user_key, extras=extras)
            user = response[current_user_key]
            comment_data['comments'] += user['comments']
            start += len(user['comments'])
            if len(user['comments']) < count:
                break
        print 'got comments'

        print 'getting replies to %s comments' % len(comment_data['comments'])
        replies_template = '[{"field": "comments", "start": %d, "count": %d, "extras": [{"field": "commenter", "extras": "username"}]}]'
        for i, comment in enumerate(comment_data['comments']):
            if i and not i % 10:
                print i,
                sys.stdout.flush()
            comment['replies'] = []
            start = 0
            count = 20
            commentKey = comment['key']
            while True:
                if start:
                    print start,
                    sys.stdout.flush()
                repliesResponse = self.rdio.get(keys=commentKey, extras=replies_template % (start, count))
                comment_replies = repliesResponse[commentKey]['comments']
                comment['replies'] += comment_replies
                start += len(comment_replies)
                if len(comment_replies) < count:
                    break
        return comment_data
