from pathlib import Path
from unittest.mock import Mock

import pytest

from zotify.config import Config
from zotify.const import (DISABLE_DIRECTORY_ARCHIVES, OPTIMIZED_DOWNLOADING,
                          SKIP_EXISTING, SKIP_PREVIOUSLY_DOWNLOADED)
from zotify.metadata import SongArchive


def test_directory_archive_writes_five_manager_fields(track_graph):
    track, stack = track_graph(artist='First Artist', title='Song')
    path = track.output_path(stack)
    track.create_download_directory(path.parent)
    archive = SongArchive(path.parent)
    archive.add_obj(track, path)
    row = Path(archive.path).read_text(encoding='utf-8').rstrip('\n').split('\t')
    assert len(row) == 5
    assert row[0] == track.id
    assert row[1]
    assert row[2:4] == ['First Artist', 'Song']
    assert row[4] == 'First Artist - Song.mp3'


def test_reusing_archive_instance_appends_instead_of_truncating(track_graph):
    track, stack = track_graph()
    path = track.output_path(stack)
    track.create_download_directory(path.parent)
    archive = SongArchive(path.parent)
    archive.add_obj(track, path)
    track2, _ = track_graph(title='Second', track_id='5' * 22)
    archive.add_obj(track2, path.with_name('Artist - Second.mp3'))
    assert archive.ids() == [track.id, track2.id]


def test_global_archive_retains_upstream_isrc(track_graph):
    track, stack = track_graph()
    path = track.output_path(stack)
    archive = SongArchive()
    archive.add_obj(track, path)
    row = Path(archive.path).read_text(encoding='utf-8').rstrip('\n').split('\t')
    assert len(row) == 6
    assert row[4] == str(path)
    assert row[5] == track.isrc


def test_tsv_metadata_cannot_add_columns_or_rows(track_graph):
    track, stack = track_graph(artist='First\tArtist', title='Title\r\nNew line')
    path = track.output_path(stack)
    track.create_download_directory(path.parent)
    archive = SongArchive(path.parent)
    archive.add_obj(track, path)
    lines = Path(archive.path).read_text(encoding='utf-8').splitlines()
    assert len(lines) == 1
    fields = lines[0].split('\t')
    assert len(fields) == 5
    assert fields[2:4] == ['First Artist', 'Title  New line']


def test_legacy_parser_preserves_whitespace_in_last_field(tmp_path):
    archive = SongArchive(tmp_path)
    entry = archive._parse_entry_str('id\tdate\tArtist\tTitle\t Artist - Title.mp3 \n')
    assert entry[archive.ITEM_PATH] == Path(' Artist - Title.mp3 ')


def test_missing_archived_file_does_not_skip_download(track_graph):
    track, stack = track_graph()
    path = track.output_path(stack)
    track.create_download_directory(path.parent)
    SongArchive(path.parent).add_obj(track, path)
    assert not track.check_skippable(stack)
    assert not track._real_filepaths


def test_empty_archived_file_does_not_skip_download(track_graph):
    track, stack = track_graph()
    path = Path(track.output_path(stack))
    track.create_download_directory(path.parent)
    path.touch()
    SongArchive(path.parent).add_obj(track, path)
    assert not track.check_skippable(stack)


def test_existing_archived_file_skips_download(track_graph):
    track, stack = track_graph()
    path = Path(track.output_path(stack))
    track.create_download_directory(path.parent)
    path.write_bytes(b'fixture-audio')
    SongArchive(path.parent).add_obj(track, path)
    assert track.check_skippable(stack)
    assert track._real_filepaths[stack] == path


@pytest.mark.parametrize('optimized', [False, True])
@pytest.mark.parametrize('artist,title,track_id,filename', [
    ('will.i.am', '#thatPOWER', '01TuObJVd7owWchVRuQbQw',
     'will.i.am - _thatPOWER.mp3'),
    ('David Guetta', "Who's That Chick? (feat. Rihanna)", '6qUSs4FDzZUdAhY6JDIJfa',
     "David Guetta - Who's That Chick_ (feat. Rihanna).mp3"),
    ('Kesha', 'Blah Blah Blah (feat. 3OH!3)', '7lWUJpax919G4JdaFEVmCy',
     'Kesha - Blah Blah Blah (feat. 3OH_3).mp3'),
])
def test_manager_repaired_archive_reuses_punctuation_track_without_prompt(
        track_graph, manager_modules, monkeypatch, optimized,
        artist, title, track_id, filename):
    _, manager_archive, _ = manager_modules
    Config.Values.update({OPTIMIZED_DOWNLOADING: optimized,
                          SKIP_EXISTING: True,
                          DISABLE_DIRECTORY_ARCHIVES: False,
                          SKIP_PREVIOUSLY_DOWNLOADED: False})
    track, stack = track_graph(artist=artist, title=title, track_id=track_id,
                               playlist='girl music (música gay)')
    path = Path(track.output_path(stack))
    assert path.name == filename
    path.parent.mkdir(parents=True, exist_ok=True)
    original = b'existing audio fixture; do not download or overwrite'
    path.write_bytes(original)
    assert SongArchive(path.parent).obj_in_archive(track) is None

    entries = [{'id': track_id, 'artist': artist, 'title': title}]
    assert manager_archive.reconcile_song_ids_flip_ids(str(path.parent), entries) == (1, 0, 0)
    assert SongArchive(path.parent).obj_in_archive(track) == path
    prompt = Mock(side_effect=AssertionError('A recognized track must not prompt'))
    stream = Mock(side_effect=AssertionError('An existing track must not fetch audio'))
    monkeypatch.setattr('zotify.api.request_suffixed_download_approval', prompt)
    monkeypatch.setattr(track, 'fetch_stream', stream)

    track.download(stack)
    assert track._real_filepaths[stack] == path
    assert path.read_bytes() == original
    assert set(path.parent.glob('*.mp3')) == {path}
    prompt.assert_not_called()
    stream.assert_not_called()
    assert manager_archive.reconcile_song_ids_flip_ids(str(path.parent), entries) == (0, 0, 0)
    track.download(stack)
    prompt.assert_not_called()
    stream.assert_not_called()


def test_archive_reads_legacy_five_and_upstream_six_fields(tmp_path):
    archive = SongArchive(tmp_path)
    Path(archive.path).write_text('old\tdate\tArtist\tTitle\tArtist - Title.mp3\n'
                            'new\tdate\tArtist\tTitle2\tArtist - Title2.mp3\tISRC\n', encoding='utf-8')
    assert archive.ids() == ['old', 'new']
    assert archive.isrcs() == ['', 'ISRC']
    assert archive.paths() == [tmp_path / 'Artist - Title.mp3', tmp_path / 'Artist - Title2.mp3']
