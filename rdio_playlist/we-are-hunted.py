#!/usr/bin/env python

FEED = 'http://wearehunted.com/chart.rss'
PLAYLIST_NAME = 'We Are Hunted'
PLAYLIST_DESC = 'We Are Hunted\'s Emerging Tracks'

import logging
import sys

from feedparser import parse
from playlistcreator import PlaylistCreator

logging.basicConfig(level=logging.ERROR)

pc = PlaylistCreator()
if not pc.authenticated:
    print 'You need to authenticate by running ./authenticate.py first'
    sys.exit(0)

# parse the feed
feed = parse(FEED)
# get the titles of the entries
titles = [title for title in [entry['title'] for entry in feed['entries']]]
# split those titles into (artistname, trackname)
tracks = [title.split(' - ', 1) for title in titles]
# make a playlist
pc.make_playlist(PLAYLIST_NAME, PLAYLIST_DESC, tracks)
