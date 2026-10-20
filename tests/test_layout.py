from pathlib import Path

import pytest
from zotify.config import Config
from zotify.api import Content, Episode, ParentStack, Show, Track
from zotify.const import ROOT_PODCAST_PATH



def test_compatibility_defaults():
    assert Config.get_download_format() == 'mp3'
    assert Track._codec == 'libmp3lame'
    assert Track._ext == 'mp3'
    assert not Config.get_skip_previously_downloaded()
    assert Config.get_output('Playlist') == '{playlist}/{artist} - {song_name}'


def test_default_playlist_is_flat_first_artist_only(track_graph):
    track, stack = track_graph(artist='First Artist', playlist='My/Playlist#')
    path = track.output_path(stack)
    assert path.relative_to(Config.get_root_path()) == Path('My_Playlist_/First Artist - Title.mp3')
    assert 'Featured Artist' not in path.name


@pytest.mark.parametrize(('artist', 'title'), [
    ('CON', 'AUX'), ('Artist/', 'Title#'), ('Björk', 'Café!*?"\\'),
    (' leading ', ' trailing . '),
])
def test_assembled_filename_matches_manager_contract(track_graph, artist, title):
    track, stack = track_graph(artist=artist, title=title)
    # Explicit template isolates rendering from the default-layout change.
    path = track.fill_output_template(stack, '{playlist}/{artist} - {song_name}')
    assert path.stem == Content.fix_filename(f'{artist} - {title}')
    assert path.parent.name == 'Playlist'


@pytest.mark.parametrize('playlist', ['.', '..'])
def test_playlist_metadata_cannot_be_a_dot_directory(track_graph, playlist):
    track, stack = track_graph(playlist=playlist)
    with pytest.raises(ValueError, match='directory'):
        track.fill_output_template(stack)
    # The upstream caller catches invalid templates and uses a safe ID path.
    path = track.output_path(stack)
    assert path.parent == Config.get_root_path()
    assert path.name == track.id + '.mp3'


@pytest.fixture
def episode_graph(tmp_path, monkeypatch):
    podcast_root = tmp_path / 'podcasts'
    podcast_root.mkdir()
    Config.Values[ROOT_PODCAST_PATH] = str(podcast_root)
    monkeypatch.setattr(Episode, '_path_root', Config.get_root_podcast_path())

    def make(show_name):
        show = Show('show:' + '5' * 22)
        show.name = show_name
        episode = Episode('episode:' + '6' * 22)
        episode.name, episode.show = 'Episode Title', show
        show.adopt(episode)
        return episode, ParentStack([show, episode])
    return make


@pytest.mark.parametrize('show_name', ['.', '..'])
def test_episode_renderer_rejects_dot_directory(episode_graph, show_name):
    episode, stack = episode_graph(show_name)
    with pytest.raises(ValueError, match='directory'):
        episode.fill_output_template(stack)


@pytest.mark.parametrize('show_name', ['.', '..'])
def test_episode_dot_directory_falls_back_within_podcast_root(episode_graph, show_name):
    episode, stack = episode_graph(show_name)
    root = Path(Config.get_root_podcast_path()).resolve()
    path = Path(episode.output_path(stack)).resolve()
    assert path.is_relative_to(root)
    assert path == root / f'{episode.id}.{episode._ext}'


def test_normal_episode_show_layout_still_supported(episode_graph):
    episode, stack = episode_graph('Normal Show')
    expected = Config.get_root_podcast_path() / 'Normal Show' / f'Normal Show - Episode Title.{episode._ext}'
    assert episode.fill_output_template(stack) == expected
    assert episode.output_path(stack) == expected


def test_explicit_upstream_template_still_supported(track_graph):
    track, stack = track_graph()
    track.track_number = 3
    path = track.fill_output_template(stack, 'Custom/{track_number}_{artists}_{song_name}')
    assert path.stem == '03_Artist, Featured Artist_Title'
