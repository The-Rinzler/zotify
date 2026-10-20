"""Isolated regression tests for local playlist tracks."""
import os
import sys
import types
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock, patch


class Dummy:
    pass


class SessionBuilder:
    def __init__(self):
        self.conf = types.SimpleNamespace(store_credentials=False)


SessionStub = type("Session", (), {"Builder": SessionBuilder})
OAuthStub = type("OAuth", (), {"OAUTH_PKCE_TOKEN": "oauth-pkce"})
AuthenticationTypeStub = type(
    "AuthenticationType", (), {"keys": classmethod(lambda cls: ["unknown", "password"])}
)


def add_stub(name, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    if "." in name:
        module.__path__ = []
    sys.modules[name] = module
    return module


# Only import-time interfaces used by the API/metadata path are stubbed.
add_stub("ffmpy", FFmpeg=Dummy, FFprobe=Dummy)
music_tag = add_stub("music_tag", __path__=[], AudioFile=Dummy, load_file=lambda *a, **k: None)
add_stub("music_tag.file", TAG_MAP_ENTRY=Dummy, MetadataItem=Dummy)
add_stub("music_tag.mp4", freeform_set=lambda *a, **k: None)
add_stub("mutagen", __path__=[], FileType=Dummy)
add_stub("mutagen.id3", TXXX=Dummy)
add_stub("tabulate", tabulate=lambda *a, **k: "")
tqdm = add_stub("tqdm", tqdm=lambda *a, **k: Dummy())
tqdm.__path__ = []
add_stub("tqdm.auto", tqdm=lambda *a, **k: Dummy())
add_stub("librespot", __path__=[])
add_stub("librespot.metadata", Id=Dummy)
add_stub("librespot.audio", FeederException=Exception,
         CdnManager=types.SimpleNamespace(Streamer=Dummy), CdnFeedHelper=Dummy)
add_stub("librespot.audio.decoders", AudioQuality=Dummy,
         SuperAudioFormat=Dummy, FormatOnlyAudioQuality=Dummy)
add_stub("librespot.core", Session=SessionStub, OAuth=OAuthStub,
         MercuryRequests=types.SimpleNamespace(keymaster_client_id="stub"), ApiClient=Dummy)
add_stub("librespot.proto", __path__=[])
add_stub("librespot.proto.Authentication_pb2", AuthenticationType=AuthenticationTypeStub)
add_stub("librespot.proto.Metadata_pb2", AudioFile=Dummy)

source_root = os.environ.get("ZOTIFY_SRC_PATH", str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, source_root)
from zotify.config import CONFIG_VALUES, DEFAULT, TYPE, Zotify
from zotify.utils import safe_typecast

Zotify.CONFIG.Values.update({
    key: safe_typecast(entry, DEFAULT, entry[TYPE])
    for key, entry in CONFIG_VALUES.items()
})

from zotify import api, metadata

api.Printer.hashtaged = lambda *args, **kwargs: None
api.Loader = lambda *args, **kwargs: nullcontext()


class FakeSongArchive:
    def __init__(self, *args, **kwargs):
        pass

    def obj_in_archive(self, *args, **kwargs):
        return None


class LocalFileDetectionTests(unittest.TestCase):
    def setUp(self):
        api.HierarchicalNode.ALL_NODES.clear()

    def test_playlist_local_flag_skips_metadata_and_output_expansion(self):
        query = api.Query("local-detection-test")
        playlist = api.Playlist("playlist:local-detection-test")
        track = api.Track("track:ordinary-looking-id")
        track.name = "Previously parsed song"
        track.is_playable = True
        track._hasMetadata = True
        artist = api.Artist("artist:local-detection-artist")
        track.artists = [artist]

        playlist_items = [{
            api.ITEM: {
                api.URI: "spotify:track:ordinary-looking-id",
                api.TYPE: "track",
                api.NAME: "Local Song",
                api.IS_PLAYABLE: True,
            },
            api.IS_LOCAL: True,
            api.ADDED_AT: None,
            api.ADDED_BY: None,
        }]
        with patch.object(api.Zotify, "invoke_url_nextable", return_value=playlist_items):
            payloads = playlist.fetch_items()
        parsed_track = playlist.parse_relatives(payloads, api.Track)[0]

        self.assertIs(parsed_track, track)
        self.assertTrue(track.is_local)
        output_path = Mock(return_value=Path("must-not-expand.mp3"))
        with patch.object(metadata, "SongArchive", FakeSongArchive):
            with patch.object(track, "output_path", output_path):
                self.assertTrue(track.check_skippable(api.ParentStack([query, playlist, track])))
        output_path.assert_not_called()

        metadata_request = Mock(return_value=[])
        with patch.object(query, "fetch_uris_metadata", side_effect=metadata_request):
            with patch.object(api.Zotify.CONFIG, "get_save_genres", return_value=True):
                query.conditional_metadata()
        metadata_request.assert_not_called()

    def test_local_uri_skips_before_output_expansion(self):
        track = api.Track("local:Artist:Album:Song:180")
        self.assertTrue(track.is_local)
        output_path = Mock(return_value=Path("must-not-expand.mp3"))
        with patch.object(metadata, "SongArchive", FakeSongArchive):
            with patch.object(track, "output_path", output_path):
                self.assertTrue(track.check_skippable(api.ParentStack([track])))
        output_path.assert_not_called()


if __name__ == "__main__":
    unittest.main()
