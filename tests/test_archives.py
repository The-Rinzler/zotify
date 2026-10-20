from pathlib import Path


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


def test_archive_reads_legacy_five_and_upstream_six_fields(tmp_path):
    archive = SongArchive(tmp_path)
    Path(archive.path).write_text('old\tdate\tArtist\tTitle\tArtist - Title.mp3\n'
                            'new\tdate\tArtist\tTitle2\tArtist - Title2.mp3\tISRC\n', encoding='utf-8')
    assert archive.ids() == ['old', 'new']
    assert archive.isrcs() == ['', 'ISRC']
    assert archive.paths() == [tmp_path / 'Artist - Title.mp3', tmp_path / 'Artist - Title2.mp3']
