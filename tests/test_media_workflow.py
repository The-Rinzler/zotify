"""Real FFmpeg/tag/archive pipeline; only the remote stream is synthetic."""
import io
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from mutagen.mp3 import MP3

from zotify.api import Episode, ParentStack, Playlist, Query, Track
from zotify.config import Config, Zotify
from zotify.const import (BULK_WAIT_TIME, DOWNLOAD_FORMAT, DOWNLOAD_QUALITY,
                          EXPORT_M3U8, LYRICS_TO_FILE,
                          LYRICS_TO_METADATA, OPTIMIZED_DOWNLOADING,
                          SKIP_PREVIOUSLY_DOWNLOADED, TEST_MODE, TRANSCODE_BITRATE)
from zotify.metadata import SongArchive


@pytest.mark.parametrize(('listing', 'expected'), [
    (' A....D libvorbis libvorbis encoder', ['-c:a', 'libvorbis']),
    (' A..X.D vorbis Vorbis encoder',
     ['-ac', '2', '-c:a', 'vorbis', '-strict', '-2']),
])
def test_vorbis_fixture_encoder_args_support_available_ffmpeg_encoders(listing, expected):
    assert _vorbis_encoder_args(listing) == expected


def _vorbis_encoder_args(encoder_listing):
    """Choose a Vorbis encoder available in this FFmpeg build."""
    names = {parts[1] for line in encoder_listing.splitlines()
             if len(parts := line.split()) >= 2}
    if 'libvorbis' in names:
        return ['-c:a', 'libvorbis']
    if 'vorbis' in names:
        # FFmpeg's native encoder is experimental and supports stereo only.
        return ['-ac', '2', '-c:a', 'vorbis', '-strict', '-2']
    raise ValueError('FFmpeg has no supported Vorbis encoder')


@pytest.fixture
def synthetic_stream(tmp_path, monkeypatch):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('FFmpeg and FFprobe are required for the real media smoke test')
    encoders = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'],
                              check=True, capture_output=True, text=True).stdout
    try:
        encoder_args = _vorbis_encoder_args(encoders)
    except ValueError as exc:
        pytest.skip(str(exc))
    source = tmp_path / 'synthetic-tone.ogg'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
                    '-i', 'sine=frequency=440:duration=0.15', *encoder_args, str(source)],
                   check=True, capture_output=True)
    audio = source.read_bytes()
    calls = []

    class FixtureStream:
        size = len(audio)

        def __init__(self):
            self.buffer = io.BytesIO(audio)

        def stream(self):
            return self.buffer

    def fetch(_track):
        calls.append(_track.id)
        return FixtureStream()

    monkeypatch.setattr(Track, 'fetch_stream', fetch)
    Config.Values.update({LYRICS_TO_FILE: False, LYRICS_TO_METADATA: False,
                          BULK_WAIT_TIME: 0.0, EXPORT_M3U8: True})
    return calls


def make_two_playlist_query(track, stack):
    second = Playlist('playlist:' + '6' * 22)
    second.name = 'Second Playlist'
    second.tracks_or_eps.append(track)
    second.adopt(track)
    query = Query('offline-fixture')
    query.requested_objs = [[stack[0], second]]
    return query


def test_macos_sample_selects_mp3_and_account_compatible_auto_quality():
    sample = json.loads((Path(__file__).parents[1] / 'examples/config.macos-ipod.json').read_text())
    assert sample[DOWNLOAD_FORMAT] == 'mp3'
    assert sample[DOWNLOAD_QUALITY] == 'auto'
    assert sample[TRANSCODE_BITRATE] == 'auto'


@pytest.mark.parametrize(('account', 'quality_name', 'bitrate'), [
    ('premium', 'VERY_HIGH', '320k'),
    ('free', 'HIGH', '160k'),
])
def test_auto_quality_reaches_real_mp3_encoder(
        track_graph, synthetic_stream, monkeypatch, account, quality_name, bitrate):
    Config.Values.update({DOWNLOAD_FORMAT: 'mp3', DOWNLOAD_QUALITY: 'auto',
                          TRANSCODE_BITRATE: 'auto'})
    # Controlled account fixture; this is not a real Spotify login or response.
    monkeypatch.setattr(Zotify, 'SESSION', SimpleNamespace(get_user_attribute=lambda _: account))
    _, quality, selected_bitrate = Zotify.parse_dl_quality(Config.get_download_qual_pref())
    assert quality.preferred.name == quality_name
    assert selected_bitrate == bitrate
    monkeypatch.setattr(Zotify, 'DOWNLOAD_BITRATE', selected_bitrate)
    track, stack = track_graph()
    track.download(stack)
    path = Path(track.output_path(stack))
    assert path.suffix == '.mp3'
    # Short MPEG streams report frame-rounded averages, not exact nominal bps.
    assert MP3(path).info.bitrate == pytest.approx(int(bitrate.removesuffix('k')) * 1000, rel=0.001)
    assert synthetic_stream == [track.id]


@pytest.mark.parametrize('optimized', [False, True])
def test_real_download_pipeline_copies_each_playlist(track_graph, synthetic_stream, optimized):
    Config.Values[OPTIMIZED_DOWNLOADING] = optimized
    track, stack = track_graph(artist='First Artist', title='Title#?!"*')
    query = make_two_playlist_query(track, stack)
    query.download()
    assert synthetic_stream == [track.id]  # one remote boundary, two physical copies
    files = sorted(Path(Config.get_root_path()).rglob('*.mp3'))
    assert len(files) == 2
    assert {p.parent.name for p in files} == {'Playlist', 'Second Playlist'}
    assert {p.name for p in files} == {'First Artist - Title___"*.mp3'}
    for path in files:
        media = MP3(path)
        assert media.info.length > 0
        assert media.tags['TIT2'].text == [track.name]
        assert media.tags['TPE1'].text == ['First Artist, Featured Artist']
        assert SongArchive(path.parent).ids() == [track.id]
        fields = (path.parent / '.song_ids').read_text().rstrip('\n').split('\t')
        assert len(fields) == 5 and fields[4] == path.name
        playlists = list(path.parent.glob('*.m3u8'))
        assert len(playlists) == 1
        references = [line for line in playlists[0].read_text().splitlines()
                      if line and not line.startswith('#')]
        assert references == [path.name]
    assert files[0].read_bytes() == files[1].read_bytes()
    assert not list(Path(Config.get_root_path()).rglob('*.ogg'))


@pytest.mark.parametrize('optimized', [False, True])
def test_existing_playlist_copy_is_reused_for_new_playlist(
        track_graph, synthetic_stream, optimized):
    Config.Values[OPTIMIZED_DOWNLOADING] = optimized
    track, stack = track_graph()
    # A previous session left the first playlist intact and indexed.
    path = Path(track.output_path(stack))
    track.create_download_directory(path.parent)
    path.write_bytes(b'existing-playlist-fixture')
    SongArchive(path.parent).add_obj(track, path)
    query = make_two_playlist_query(track, stack)
    query.download()
    second = Path(Config.get_root_path()) / 'Second Playlist' / path.name
    assert second.is_file()
    assert second.read_bytes() == path.read_bytes()
    assert not synthetic_stream  # no download when a valid playlist copy exists
    assert SongArchive(second.parent).ids() == [track.id]


@pytest.mark.parametrize('optimized', [False, True])
@pytest.mark.parametrize('skip_global', [False, True])
def test_new_playlist_only_query_reuses_previous_session_copy(
        track_graph, synthetic_stream, optimized, skip_global):
    Config.Values.update({OPTIMIZED_DOWNLOADING: optimized,
                          SKIP_PREVIOUSLY_DOWNLOADED: skip_global})
    track, stack = track_graph()
    source = Path(track.output_path(stack))
    track.create_download_directory(source.parent)
    source.write_bytes(b'previous-session-copy-fixture')
    SongArchive(source.parent).add_obj(track, source)
    SongArchive().add_obj(track, source)
    query = make_two_playlist_query(track, stack)
    query.requested_objs[0].pop(0)  # old playlist is NOT requested this session
    query.download()
    target = Path(Config.get_root_path()) / 'Second Playlist' / source.name
    assert target.is_file()
    assert target.read_bytes() == source.read_bytes()
    assert not synthetic_stream
    assert SongArchive(target.parent).ids() == [track.id]
    assert track._real_filepaths and target in track._real_filepaths.values()


@pytest.mark.parametrize('optimized', [False, True])
def test_global_ogg_does_not_suppress_required_mp3_copy(track_graph, synthetic_stream, optimized):
    Config.Values.update({OPTIMIZED_DOWNLOADING: optimized,
                          SKIP_PREVIOUSLY_DOWNLOADED: True})
    track, stack = track_graph()
    source = Path(track.output_path(stack)).with_suffix('.ogg')
    track.create_download_directory(source.parent)
    source.write_bytes(b'old-ogg-fixture')
    SongArchive().add_obj(track, source)
    query = make_two_playlist_query(track, stack)
    query.requested_objs[0].pop(0)
    query.download()
    target = Path(Config.get_root_path()) / 'Second Playlist' / source.with_suffix('.mp3').name
    assert target.is_file() and MP3(target).info.length > 0
    assert synthetic_stream == [track.id]
    assert source.read_bytes() == b'old-ogg-fixture'


@pytest.mark.parametrize('optimized', [False, True])
def test_dry_run_does_not_clone_previous_session_source(track_graph, synthetic_stream, optimized):
    Config.Values.update({OPTIMIZED_DOWNLOADING: optimized, TEST_MODE: True})
    track, stack = track_graph()
    source = Path(track.output_path(stack))
    track.create_download_directory(source.parent)
    source.write_bytes(b'dry-run-source-fixture')
    SongArchive().add_obj(track, source)
    query = make_two_playlist_query(track, stack)
    query.requested_objs[0].pop(0)
    query.download()
    assert not (Path(Config.get_root_path()) / 'Second Playlist').exists()
    assert not synthetic_stream
    assert source.read_bytes() == b'dry-run-source-fixture'


@pytest.mark.parametrize('optimized', [False, True])
def test_directory_ogg_is_not_downloaded_track_or_clone_source(
        track_graph, synthetic_stream, optimized, tmp_path):
    Config.Values[OPTIMIZED_DOWNLOADING] = optimized
    track, stack = track_graph()
    source = Path(track.output_path(stack)).with_suffix('.ogg')
    track.create_download_directory(source.parent)
    shutil.copyfile(tmp_path / 'synthetic-tone.ogg', source)
    original = source.read_bytes()
    SongArchive(source.parent).add_obj(track, source)
    assert not track.check_skippable(stack)
    assert not track._downloaded and not track._real_filepaths
    query = make_two_playlist_query(track, stack)
    query.download()
    files = sorted(Path(Config.get_root_path()).rglob('*.mp3'))
    assert len(files) == 2
    assert synthetic_stream == [track.id]
    assert files[0].read_bytes() == files[1].read_bytes()
    assert all(MP3(path).info.length > 0 for path in files)
    assert source.read_bytes() == original
    for path in files:
        assert SongArchive(path.parent).obj_in_archive(track, required_suffix='.mp3') == path
    assert SongArchive().obj_in_archive(track, required_suffix='.mp3') in files


@pytest.mark.parametrize('optimized', [False, True])
def test_older_global_ogg_does_not_mask_later_mp3(
        track_graph, synthetic_stream, optimized, tmp_path):
    Config.Values.update({OPTIMIZED_DOWNLOADING: optimized,
                          SKIP_PREVIOUSLY_DOWNLOADED: True})
    track, stack = track_graph()
    source = Path(track.output_path(stack))
    track.create_download_directory(source.parent)
    ogg = source.with_suffix('.ogg')
    shutil.copyfile(tmp_path / 'synthetic-tone.ogg', ogg)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(ogg),
                    '-c:a', 'libmp3lame', str(source)], check=True, capture_output=True)
    original = source.read_bytes()
    archive = SongArchive()
    archive.add_obj(track, ogg)
    archive.add_obj(track, source)
    query = make_two_playlist_query(track, stack)
    query.requested_objs[0].pop(0)
    query.download()
    target = Path(Config.get_root_path()) / 'Second Playlist' / source.name
    assert not synthetic_stream
    assert target.read_bytes() == original == source.read_bytes()
    assert MP3(target).info.length > 0
    assert archive.obj_in_archive(track) == ogg  # unfiltered callers are unchanged
    assert archive.obj_in_archive(track, required_suffix='.mp3') == source


@pytest.mark.parametrize('optimized', [False, True])
def test_track_clone_rejects_mismatched_suffix(track_graph, synthetic_stream, optimized, tmp_path):
    Config.Values[OPTIMIZED_DOWNLOADING] = optimized
    track, stack = track_graph()
    source = tmp_path / 'synthetic-tone.ogg'
    track._real_filepaths[stack] = source
    assert not track.clone_file(stack, source)
    assert not Path(track.output_path(stack)).exists()


@pytest.mark.parametrize('optimized', [False, True])
def test_global_ogg_does_not_skip_nonplaylist_track(track_graph, synthetic_stream, optimized, tmp_path):
    Config.Values.update({OPTIMIZED_DOWNLOADING: optimized,
                          SKIP_PREVIOUSLY_DOWNLOADED: True})
    track, _ = track_graph()
    SongArchive().add_obj(track, tmp_path / 'synthetic-tone.ogg')
    assert not track.check_skippable(ParentStack([Query('direct'), track]))
    assert not track._downloaded


@pytest.mark.parametrize('optimized', [False, True])
def test_episode_archive_remains_suffix_agnostic(
        track_graph, synthetic_stream, optimized, tmp_path, monkeypatch):
    Config.Values.update({OPTIMIZED_DOWNLOADING: optimized,
                          SKIP_PREVIOUSLY_DOWNLOADED: True})
    _, stack = track_graph()
    episode = Episode('episode:' + '7' * 22)
    source = tmp_path / 'synthetic-tone.ogg'
    SongArchive().add_obj(episode, source)
    monkey_stack = ParentStack([stack[0], episode])
    monkeypatch.setattr(episode, 'output_path', lambda *_: tmp_path / 'episode.copy')
    assert episode.check_skippable(monkey_stack)
    assert source in episode._real_filepaths.values()
    monkeypatch.setattr(episode, 'output_path', lambda *_: tmp_path / 'cloned.copy')
    # Isolate cloning from the already-tested archive skip decision.
    monkeypatch.setattr(monkey_stack, 'check_skippable', lambda: False)
    assert episode.clone_file(monkey_stack)
    assert (tmp_path / 'cloned.copy').read_bytes() == source.read_bytes()


def test_mp3_failure_never_archives_an_ogg_fallback(track_graph, synthetic_stream, monkeypatch):
    track, stack = track_graph()
    monkeypatch.setattr(track, 'convert_audio_format', lambda *_: None)
    track.download(stack)
    assert not track._downloaded
    assert not track._real_filepaths
    assert not SongArchive().ids()
    assert not SongArchive(track.output_path(stack).parent).ids()
    assert not list(Path(Config.get_root_path()).rglob('*.ogg'))
    assert list(Path(Config.get_root_path()).rglob('*.tmp'))


def test_manager_consumes_archive_and_builds_independent_flat_library(
        track_graph, synthetic_stream, manager_modules, tmp_path):
    manager_utils, manager_archives, manager_library = manager_modules
    track, stack = track_graph(artist='First Artist', title='Title#?!"*')
    make_two_playlist_query(track, stack).download()
    root = Path(Config.get_root_path())
    sources = sorted(root.rglob('*.mp3'))
    original = {p: p.read_bytes() for p in sources}
    for path in sources:
        result = manager_archives.cleanup_song_ids_orphans(str(path.parent))
        assert result == {'kept': 1, 'dropped_orphans': 0}
        # Exercise the manager's real filename/M3U generation contract, offline.
        metadata = manager_utils.write_playlist_to_m3u8(
            [{'track': {'name': track.name, 'artists': [{'name': track.artists[0].name}]}}],
            str(path.parent / ('manager-' + path.parent.name + '.m3u8')))
        assert metadata[0][0] == path.name
    consolidated = tmp_path / 'Consolidated Library'
    manager_library.consolidate_library([str(root)], str(consolidated))
    assert [p.name for p in consolidated.glob('*.mp3')] == [sources[0].name]
    assert not list(consolidated.glob('*/'))
    assert not (consolidated / '.song_ids').exists()
    for path, before in original.items():
        assert path.read_bytes() == before
    for playlist in consolidated.glob('*.m3u8'):
        refs = [line for line in playlist.read_text().splitlines()
                if line and not line.startswith('#')]
        assert refs == [sources[0].name]
        assert all((consolidated / name).is_file() for name in refs)
