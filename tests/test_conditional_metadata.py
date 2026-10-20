"""Bound optional album enrichment using controlled, offline metadata payloads."""
from base64 import b64encode
from contextlib import nullcontext
from unittest.mock import Mock

import pytest

from zotify import api
from zotify.config import Config, Zotify
from zotify.const import (DOWNLOAD_PARENT_ALBUM, MD_DISC_TRACK_TOTALS,
                          MD_SAVE_GENRES)


def gid(index):
    return b64encode(index.to_bytes(16, 'big')).decode()


def track_uri(index):
    return 'track:' + Zotify.id_from_gid(gid(index))


def album_response(album_id, track_ids):
    """Librespot album shape: disc entries contain GIDs, not full tracks."""
    return {
        'uri': f'spotify:album:{album_id}', 'type': 'album', 'name': 'Fixture Album',
        'disc': [
            {'number': 1, 'track': [{'gid': gid(i)} for i in track_ids[:2]]},
            {'number': 2, 'track': [{'gid': gid(i)} for i in track_ids[2:]]},
        ],
    }


def playlist_query():
    query = api.Query('conditional-metadata-test')
    playlist = api.Playlist('playlist:fixture')
    query.requested_objs = [[playlist]]
    album = api.Album('album:fixture')
    track = api.Track(track_uri(1))
    track.name, track.album, track.is_playable = 'Fixture Song', album, True
    playlist.tracks_or_eps.append(track)
    playlist.adopt(track)
    Config.Values.update({MD_SAVE_GENRES: False, MD_DISC_TRACK_TOTALS: True,
                          DOWNLOAD_PARENT_ALBUM: False})
    return query, album, track


def test_totals_only_does_not_fetch_off_playlist_album_tracks(monkeypatch):
    query, album, track = playlist_query()
    requests = []

    def fetch(uris, cls, **kwargs):
        requests.append((list(uris), cls))
        if cls is api.Album:
            return [album_response('fixture', range(1, 6))]
        return []

    monkeypatch.setattr(query, 'fetch_uris_metadata', fetch)
    query.conditional_metadata()

    assert requests == [([album.uri], api.Album)]
    assert album.total_discs == 2
    assert album.total_tracks == 5
    assert track.album is album
    assert track.disc_number == 1 and track.track_number == 1
    assert query.requested_objs == [[next(n for n in query.ALL_NODES
                                          if isinstance(n, api.Playlist))]]


def test_complete_librespot_album_supplies_track_and_disc_counts():
    album = api.Album('album:fixture')
    album.parse_metadata(None, album_response('fixture', range(1, 6)))
    assert album.total_tracks == 5
    assert album.total_discs == 2


@pytest.mark.parametrize('totals', [False, True])
def test_parent_album_mode_still_expands_playable_nonlocal_tracks(monkeypatch, totals):
    query, album, track = playlist_query()
    Config.Values[DOWNLOAD_PARENT_ALBUM] = True
    Config.Values[MD_DISC_TRACK_TOTALS] = totals
    local = api.Track('local:Artist:Album:Song:180')
    unavailable = api.Track('track:unavailable')
    unavailable.is_playable = False
    album.tracks.extend([local, unavailable])
    requests = []

    def fetch(uris, cls, **kwargs):
        uris = list(uris)
        requests.append((uris, cls))
        if cls is api.Album:
            return [album_response('fixture', range(1, 6))]
        return [{'uri': 'spotify:' + uri, 'type': 'track', 'name': 'Full Song',
                 'is_playable': True} for uri in uris]

    monkeypatch.setattr(query, 'fetch_uris_metadata', fetch)
    query.conditional_metadata()
    assert requests == [([album.uri], api.Album),
                        ([track_uri(i) for i in range(1, 6)], api.Track)]
    assert track in album.tracks


def test_totals_only_skips_albums_of_local_and_unavailable_tracks(monkeypatch):
    query = api.Query('skipped-tracks')
    Config.Values.update({MD_SAVE_GENRES: False, MD_DISC_TRACK_TOTALS: True,
                          DOWNLOAD_PARENT_ALBUM: False})
    for uri in ('local:Artist:Album:Song:180', 'track:unavailable'):
        track = api.Track(uri)
        track.is_playable = False if not track.is_local else True
        track.album = api.Album('album:' + uri.split(':')[0])
    fetch = Mock()
    monkeypatch.setattr(query, 'fetch_uris_metadata', fetch)
    query.conditional_metadata()
    fetch.assert_not_called()


def test_disabled_album_enrichment_makes_no_requests(monkeypatch):
    query, _, _ = playlist_query()
    Config.Values[MD_DISC_TRACK_TOTALS] = False
    fetch = Mock()
    monkeypatch.setattr(query, 'fetch_uris_metadata', fetch)
    query.conditional_metadata()
    fetch.assert_not_called()


def test_totals_request_count_scales_with_albums_not_album_tracks(monkeypatch):
    query, _, _ = playlist_query()
    album_payloads = {'album:fixture': album_response('fixture', range(1, 21))}
    for index in range(1, 12):
        album_id = Zotify.id_from_gid(gid(1000 + index))
        album = api.Album('album:' + album_id)
        track = api.Track(track_uri(index * 20 + 1))
        track.album, track.is_playable = album, True
        album_payloads[album.uri] = album_response(album_id, range(index * 20 + 1, index * 20 + 21))
    calls = []

    def fetch(cls, uri):
        calls.append((cls, uri))
        assert cls is api.Album, 'Totals-only must not fetch full album tracks'
        return album_payloads[uri]

    monkeypatch.setattr(api, 'Loader', lambda *a, **kw: nullcontext())
    monkeypatch.setattr(Config, 'permit_legacy_api', classmethod(lambda cls: False))
    monkeypatch.setattr(Config, 'permit_client_api', classmethod(lambda cls: False))
    monkeypatch.setattr(Zotify, 'ALLOW_LIBRE_BULK', False)
    monkeypatch.setattr(Zotify, 'invoke_libre_md', fetch)
    query.conditional_metadata()
    assert len(calls) == len(album_payloads) == 12
    assert {uri for _, uri in calls} == set(album_payloads)
    for uri in album_payloads:
        album = api.Content.get_if_exists(uri)
        assert isinstance(album, api.Album)
        assert album.total_tracks == 20 and album.total_discs == 2


def test_partial_web_album_preserves_reported_total():
    album = api.Album('album:partial')
    album.parse_metadata(None, {
        'uri': 'spotify:album:partial', 'type': 'album', 'name': 'Partial Album',
        'total_tracks': 100,
        'tracks': {'items': [{'uri': 'spotify:' + track_uri(1), 'type': 'track',
                              'disc_number': 1}], 'next': 'https://example.invalid/next'},
    })
    assert album.total_tracks == 100
    assert album.total_discs is None
    assert album._needs_expansion


def test_sequential_metadata_loader_identifies_each_request(monkeypatch):
    loaders = []
    descriptions = []

    class RecordingLoader(nullcontext):
        def __init__(self, desc, **kwargs):
            super().__init__()
            self.desc = desc
            loaders.append(self)

    def fetch(uri):
        descriptions.append(loaders[-1].desc)
        return {'uri': uri}

    monkeypatch.setattr(api, 'Loader', RecordingLoader)
    monkeypatch.setattr(Config, 'permit_legacy_api', classmethod(lambda cls: False))
    monkeypatch.setattr(Config, 'permit_client_api', classmethod(lambda cls: False))
    monkeypatch.setattr(Zotify, 'ALLOW_LIBRE_BULK', False)
    monkeypatch.setattr(api.Album, 'fetch_metadata', fetch)
    uris = ['album:first', 'album:second', 'album:third']
    assert api.Content.fetch_uris_metadata(uris, api.Album, loader_text='track/disc total') == [
        {'uri': uri} for uri in uris]
    for index, (description, uri) in enumerate(zip(descriptions, uris), 1):
        assert f'{index}/3' in description
        assert uri in description
