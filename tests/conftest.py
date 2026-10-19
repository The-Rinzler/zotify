"""Offline tests: isolate all paths before importing graph classes."""
import importlib.util
import os
import socket
from pathlib import Path
import tempfile

import pytest

from zotify.config import Config, CONFIG_VALUES, DEFAULT, TYPE
from zotify.const import ROOT_PATH, ROOT_PODCAST_PATH, SONG_ARCHIVE_LOCATION
from zotify.utils import safe_typecast

# api.py binds paths and codecs at import time, just as the CLI does after load().
_SANDBOX = tempfile.TemporaryDirectory(prefix="zotify-tests-")
Config.Values = {key: safe_typecast(spec, DEFAULT, spec[TYPE])
                 for key, spec in CONFIG_VALUES.items()}
Config.Values.update({ROOT_PATH: str(Path(_SANDBOX.name) / "music"),
                      ROOT_PODCAST_PATH: str(Path(_SANDBOX.name) / "podcasts"),
                      SONG_ARCHIVE_LOCATION: str(Path(_SANDBOX.name) / ".song_archive")})

from zotify.api import Artist, Content, HierarchicalNode, ParentStack, Playlist, Track  # noqa: E402
from zotify.metadata import SongArchive  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_library(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('Offline test attempted a network connection')
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    monkeypatch.setattr(Config, "Values", Config.Values.copy())
    Config.Values.update({ROOT_PATH: str(tmp_path / "music"),
                          SONG_ARCHIVE_LOCATION: str(tmp_path / ".song_archive")})
    (tmp_path / "music").mkdir()
    monkeypatch.setattr(Content, "_path_root", Path(Config.Values[ROOT_PATH]))
    monkeypatch.setattr(HierarchicalNode, "ALL_NODES", {})
    monkeypatch.setattr(ParentStack, "SKIPPABLE_CACHE", {})
    monkeypatch.setattr(SongArchive, "UPDATE_GLOBAL", False)


@pytest.fixture
def track_graph():
    def make(artist='Artist', title='Title', playlist='Playlist', track_id='1' * 22):
        track = Track(f'track:{track_id}')
        track.name, track.is_playable = title, True
        track.duration_ms, track.isrc = 1000, 'TEST00000001'
        track.artists = [Artist('artist:' + '2' * 22), Artist('artist:' + '3' * 22)]
        track.artists[0].name, track.artists[1].name = artist, 'Featured Artist'
        parent = Playlist('playlist:' + '4' * 22)
        parent.name = playlist
        parent.tracks_or_eps.append(track)
        parent.adopt(track)
        return track, ParentStack([parent, track])
    return make


@pytest.fixture
def manager_modules(monkeypatch, tmp_path):
    """Opt-in integration with the user's real manager, never its live data."""
    root = os.environ.get("ZOTIFY_MANAGER_SOURCE")
    if not root:
        pytest.skip("Set ZOTIFY_MANAGER_SOURCE for cross-repository integration")
    assert root is not None
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.syspath_prepend(root)
    modules = []
    for name in ("utils", "song_ids_manager", "library_manager"):
        spec = importlib.util.spec_from_file_location(name, Path(root) / f"{name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        import sys
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        modules.append(module)
    # The manager registers an exit hook: redirect its cache into the fixture.
    modules[2]._HASH_DB_PATH = tmp_path / "hashes.json"
    return modules
