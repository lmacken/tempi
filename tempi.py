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
# Copyright (C) 2012-2014, Luke Macken <lmacken@redhat.com>
"""
tempi.py - Add tempo metadata to your music collection using The Echo Nest.
"""

__version__ = '0.2.1'

import os
import sys
import sha
import time
import math
import mutagen
import pyechonest.song
import pyechonest.config
import pyechonest.catalog

from progressbar import ProgressBar, Percentage, Bar, Counter

## Add your API keys here
pyechonest.config.ECHO_NEST_API_KEY = ''
pyechonest.config.ECHO_NEST_CONSUMER_KEY = ''
pyechonest.config.ECHO_NEST_SHARED_SECRET = ''

MAX_SONGS = 100  # per catalog update


class Tempi(object):

    def __init__(self, directory):
        self.library = directory
        self.catalog = None
        self.bpm_exists = 0
        self.bpm_found = 0
        self.bpm_na = 0
        self.song_dupe = 0
        self.missing_tags = 0
        self.errors = 0

    def run(self):
        items = self.update_catalog()
        if items:
            self.update_tempo_metadata(items)

    def generate_catalog_data(self):
        """Generate a list of songs to update our Echo Nest Catalog with"""
        data = []
        songs = set()
        ids = set()
        progress = ProgressBar(widgets=['Scanning Library: ',
            LibraryProgress(), ' songs'])
        for song in progress(self.walk_library(self.library)):
            try:
                artist = song['artist'][0]
                title = song['title'][0]
            except (KeyError, IndexError):
                self.missing_tags += 1
                continue
            if song.get('bpm'):
                self.bpm_exists += 1
                continue
            if artist and title:
                id = sha.new(('%s-%s' % (artist, title))
                        .encode('utf-8', errors='ignore')).hexdigest()
                if song.filename in songs or id in ids:
                    self.song_dupe += 1
                    continue
                songs.add(song.filename)
                ids.add(id)
                data.append({
                    'action': 'update',
                    'item': {
                        'url': song.filename,
                        'item_id': id.encode('utf-8'),
                        'artist_name': artist.encode('utf-8'),
                        'song_name': title.encode('utf-8'),
                        }})
        return data

    def update_catalog(self):
        """Create a new catalog and populate it with music from our library"""
        data = self.generate_catalog_data()
        items = []
        num_songs = len(data)
        num_chunks = math.ceil(num_songs / float(MAX_SONGS))
        chunk_i = 1
        i = 0
        print("Found %d songs without tempo metadata\n" % num_songs)
        if not num_songs:
            return items
        print('Updating Catalog...')
        progress = ProgressBar(maxval=100 * num_chunks, widgets=[
            Bar(marker=u"\u2593"), Percentage()]).start()
        self.catalog = pyechonest.catalog.Catalog('tempi', type='song')
        while True:
            chunk = data[:MAX_SONGS]
            chunk_len = len(chunk)
            ticket = self.catalog.update(chunk)
            for status in self.wait_for_catalog_update(ticket):
                progress.update(int(status['percent_complete']) * chunk_i)
            items += self.catalog.get_item_dicts(buckets=['audio_summary'],
                                                 start=i, results=chunk_len)
            i += chunk_len
            chunk_i += 1
            data = data[MAX_SONGS:]
            if not data:
                break
        assert len(items) == num_songs, len(items)
        progress.finish()
        return items

    def wait_for_catalog_update(self, ticket):
        waiting = True
        while waiting:
            time.sleep(3)
            status = self.catalog.status(ticket)
            assert status['ticket_status'] != 'error', status
            yield status
            if status['ticket_status'] == 'complete':
                waiting = False

    def walk_library(self, library):
        for root, dirs, files in os.walk(self.library):
            for filename in files:
                try:
                    song = mutagen.File(os.path.join(root, filename), easy=True)
                except Exception, e:
                    print('%s: %s' % (filename, str(e)))
                    self.errors += 1
                if not song:
                    continue
                yield song

    def update_tempo_metadata(self, items):
        progress = ProgressBar(maxval=len(items), widgets=[
            Bar(marker=u"\u2593"), Percentage()])
        up, save, restore, chop = ['\x1b[' + x for x in 'FsuK']
        print('\n')
        for item in progress(items):
            tempo = item.get('audio_summary', {}).get('tempo', None)
            if tempo:
                song = mutagen.File(item['request']['url'], easy=True)
                name = '%s - %s' % (song['artist'][0], song['title'][0])
                if len(name) > 48: name = name[:45] + '...'
                sys.stdout.write("%s%sUpdating Metadata: %s (%0.2f BPM)%s%s" %
                        (save, up, name, tempo, chop, restore))
                sys.stdout.flush()
                try:
                    song['bpm'] = unicode(tempo)
                except:  # hack for mp4 files
                    song['bpm'] = [float(tempo)]
                song.save()
                self.bpm_found += 1
            else:
                self.bpm_na += 1

    def print_stats(self):
        print('')
        if self.bpm_found:
            print("Songs tagged with newly discovered BPM: %d" % self.bpm_found)
        if self.bpm_exists:
            print("Songs that already had BPM: %d" % self.bpm_exists)
        if self.bpm_na:
            print("Songs with unknown BPM: %d" % self.bpm_na)
        if self.missing_tags:
            print("Songs with missing tags: %d" % self.missing_tags)
        if self.song_dupe:
            print("Duplicate songs: %d" % self.song_dupe)
        if self.errors:
            print("Errors accessing songs: %d" % self.errors)

    def close(self):
        if self.catalog:
            self.catalog.delete()


class LibraryProgress(Counter):
    """A custom progress bar used when scanning the library"""
    def update(self, pbar):
        return str(int(pbar.currval) + 1)


def main():
    if len(sys.argv) != 2:
        print("Usage: python %s <directory of music>" % sys.argv[0])
        sys.exit(-1)
    try:
        import fabulous.text
        print(str(fabulous.text.Text('tempi', shadow=True,
            font='DejaVuSansMono', color='#73d216')).rstrip() +
            ' v%s' % __version__)
    except ImportError:
        print('tempi v%s' % __version__)

    tempi = Tempi(sys.argv[1])
    try:
        tempi.run()
    finally:
        tempi.print_stats()
        tempi.close()
