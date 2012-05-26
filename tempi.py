#!/usr/bin/env python
"""
tempi.py - Add tempo metadata to your music using The Echo Nest
===============================================================

.. author:: Luke Macken <lmacken@redhat.com>
.. license:: GPLv3+

Installing
----------

Sign up for an EchoNest API key: https://developer.echonest.com/docs

    $ sudo yum -y install python-virtualenv python-eyed3
    $ virtualenv env
    $ source env
    $ pip install pyechonest

Using
-----

First, set the echonest API key values in this file.

    $ python tempofinder.py <directory of music>
"""

import re
import os
import sys
import time
import eyeD3
import pyechonest.song
import pyechonest.config
import pyechonest.catalog

pyechonest.config.ECHO_NEST_API_KEY = ''
pyechonest.config.ECHO_NEST_CONSUMER_KEY = ''
pyechonest.config.ECHO_NEST_SHARED_SECRET = ''

EXTENSIONS = ('mp3', 'flac', 'ogg')


class Tempi(object):

    def __init__(self, directory):
        self.catalog = pyechonest.catalog.Catalog('tempofinder', type='song')
        self.library = directory
        self.errors = 0
        self.bpm_exists = 0
        self.bpm_found = 0
        self.bpm_na = 0
        self.song_dupe = 0
        self.unknown_files = 0

    def run(self):
        items = self.update_catalog(self.library)
        self.update_tempo_metadata(items)

    def song_id(self, song):
        """Return a valid Echo Nest item_id for a given song"""
        return re.sub(r'[^A-Za-z0-9\._\-]', '', song)

    def update_catalog(self, library):
        data = []
        songs = {}
        ids = set()
        for song in self.walk_library(library):
            tag = eyeD3.Tag()
            try:
                tag.link(song)
                bpm = tag.getBPM()
            except Exception, e:
                print("Error: %s (%s)" % (str(e), song))
                self.errors += 1
                continue
            if bpm:
                self.bpm_exists += 1
                continue

            artist = tag.getArtist()
            title = tag.getTitle()
            if artist and title:
                id = self.song_id('%s - %s' % (artist, title))
                if song in songs or id in ids:
                    print("Skipping dupe song: %s" % song)
                    self.song_dupe += 1
                    continue
                songs[song] = True
                ids.add(id)
                data.append({
                    'action': 'update',
                    'item': {
                        'url': song,
                        'item_id': id,
                        'artist_name': artist,
                        'song_name': title,
                        }})

        num_songs = len(data)
        print("Adding %d songs to catalog" % num_songs)
        ticket = self.catalog.update(data)
        self.wait_for_catalog_update(ticket)
        items = self.catalog.get_item_dicts(buckets=['audio_summary'],
                                            results=num_songs)
        print("Got %d items back from catalog" % len(items))
        return items

    def wait_for_catalog_update(self, ticket):
        waiting = True
        while waiting:
            status = self.catalog.status(ticket)
            print("Updating Catalog (%s%%)" % status['percent_complete'])
            assert status['ticket_status'] != 'error', status
            if status['ticket_status'] == 'complete':
                waiting = False
            else:
                time.sleep(2)

    def walk_library(self, library):
        print("Scanning music...")
        for root, dirs, files in os.walk(self.library):
            for filename in files:
                if filename.split('.')[-1].lower() in EXTENSIONS:
                    yield os.path.join(root, filename)
                else:
                    self.unknown_files += 1

    def update_tempo_metadata(self, items):
        for item in items:
            tempo = item.get('audio_summary', {}).get('tempo', None)
            if tempo:
                print("%s - %s (%s BPM)" % (item['artist_name'],
                      item['song_name'], tempo))
                tag = tag = eyeD3.Tag()
                tag.link(item['request']['url'])
                tag.setBPM(tempo)
                tag.update()
                self.bpm_found += 1

    def print_stats(self):
        print("Songs tagged with newly discovered BPM: %d" % self.bpm_found)
        print("Songs that already had BPM: %d" % self.bpm_exists)
        print("Songs with unknown BPM: %d" % self.bpm_na)
        print("Duplicate songs: %d" % self.song_dupe)
        print("Unknown files: %d" % self.unknown_files)
        print("Errors: %d" % self.errors)

    def close(self):
        self.catalog.delete()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python %s <directory of music>" % sys.argv[0])
        sys.exit(-1)

    tempofinder = Tempi(sys.argv[1])
    try:
        tempofinder.run()
    finally:
        tempofinder.print_stats()
        tempofinder.close()
