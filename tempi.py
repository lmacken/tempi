#!/usr/bin/env python
# tempi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tempi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tempi.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2012, Luke Macken <lmacken@redhat.com>
"""
tempi.py - Add tempo metadata to your music collection using The Echo Nest.
"""

import re
import os
import sys
import time
import mutagen
import pyechonest.song
import pyechonest.config
import pyechonest.catalog

## Add your API keys here
pyechonest.config.ECHO_NEST_API_KEY = ''
pyechonest.config.ECHO_NEST_CONSUMER_KEY = ''
pyechonest.config.ECHO_NEST_SHARED_SECRET = ''


class Tempi(object):

    def __init__(self, directory):
        self.catalog = pyechonest.catalog.Catalog('tempi', type='song')
        self.library = directory
        self.bpm_exists = 0
        self.bpm_found = 0
        self.bpm_na = 0
        self.song_dupe = 0
        self.missing_tags = 0

    def run(self):
        items = self.update_catalog()
        self.update_tempo_metadata(items)

    def song_id(self, song):
        """Return a valid Echo Nest item_id for a given song"""
        return re.sub(r'[^A-Za-z0-9\._\-]', '', song)

    def generate_catalog_data(self):
        data = []
        songs = {}
        ids = set()
        for path, tags in self.walk_library(self.library):
            try:
                artist = tags['artist'][0]
                title = tags['title'][0]
            except (KeyError, IndexError):
                self.missing_tags += 1
                continue
            if tags.get('bpm'):
                self.bpm_exists += 1
                continue
            if artist and title:
                id = self.song_id('%s - %s' % (artist, title))
                if path in songs or id in ids:
                    self.song_dupe += 1
                    continue
                songs[path] = True
                ids.add(id)
                data.append({
                    'action': 'update',
                    'item': {
                        'url': path,
                        'item_id': id,
                        'artist_name': artist,
                        'song_name': title,
                        }})
        return data

    def update_catalog(self):
        data = self.generate_catalog_data()
        num_songs = len(data)
        print("Adding %d songs to the catalog" % num_songs)
        ticket = self.catalog.update(data)
        self.wait_for_catalog_update(ticket)
        items = self.catalog.get_item_dicts(buckets=['audio_summary'],
                                            results=num_songs)
        print("Got %d items back from catalog" % len(items))
        return items

    def wait_for_catalog_update(self, ticket):
        waiting = True
        while waiting:
            time.sleep(2)
            status = self.catalog.status(ticket)
            print("Updating catalog (%0.2f%%)" % status['percent_complete'])
            assert status['ticket_status'] != 'error', status
            if status['ticket_status'] == 'complete':
                waiting = False

    def walk_library(self, library):
        print("Scanning music...")
        for root, dirs, files in os.walk(self.library):
            for filename in files:
                url = os.path.join(root, filename)
                song = mutagen.File(url, easy=True)
                if not song:
                    continue
                yield url, song

    def update_tempo_metadata(self, items):
        for item in items:
            tempo = item.get('audio_summary', {}).get('tempo', None)
            if tempo:
                print("%s - %s (%s BPM)" % (item['artist_name'],
                      item['song_name'], tempo))
                song = mutagen.File(item['request']['url'], easy=True)
                song['bpm'] = unicode(tempo)
                song.save()
                self.bpm_found += 1
            else:
                self.bpm_na += 1

    def print_stats(self):
        print("Songs tagged with newly discovered BPM: %d" % self.bpm_found)
        print("Songs that already had BPM: %d" % self.bpm_exists)
        print("Songs with unknown BPM: %d" % self.bpm_na)
        print("Songs with missing tags: %d" % self.missing_tags)
        print("Duplicate songs: %d" % self.song_dupe)

    def close(self):
        self.catalog.delete()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python %s <directory of music>" % sys.argv[0])
        sys.exit(-1)

    tempi = Tempi(sys.argv[1])
    try:
        tempi.run()
    finally:
        tempi.print_stats()
        tempi.close()