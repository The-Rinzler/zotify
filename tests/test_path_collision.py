from io import StringIO
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

from zotify.config import Config
from zotify.const import (DISABLE_DIRECTORY_ARCHIVES, OPTIMIZED_DOWNLOADING,
                          SKIP_EXISTING, SKIP_PREVIOUSLY_DOWNLOADED)
from zotify.metadata import SongArchive
from zotify.path_collision import request_suffixed_download_approval


@pytest.mark.parametrize('optimized', [False, True])
@pytest.mark.parametrize('disable_archives', [False, True])
def test_unarchived_existing_track_path_skips_without_creating_numbered_copy(
        track_graph, monkeypatch, optimized, disable_archives):
    Config.Values.update({OPTIMIZED_DOWNLOADING: optimized,
                          SKIP_EXISTING: True,
                          DISABLE_DIRECTORY_ARCHIVES: disable_archives,
                          SKIP_PREVIOUSLY_DOWNLOADED: False})
    track, stack = track_graph()
    path = Path(track.output_path(stack))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'existing audio')
    monkeypatch.setattr(sys, 'stdin', StringIO(''))

    assert track.check_skippable(stack)
    assert path.read_bytes() == b'existing audio'
    assert SongArchive(path.parent).ids() == []
    assert not path.with_name(f'{path.stem}_1{path.suffix}').exists()


def test_interactive_approval_allows_numbered_download(track_graph, monkeypatch):
    Config.Values.update({OPTIMIZED_DOWNLOADING: True,
                          SKIP_EXISTING: True,
                          DISABLE_DIRECTORY_ARCHIVES: False,
                          SKIP_PREVIOUSLY_DOWNLOADED: False})
    track, stack = track_graph()
    path = Path(track.output_path(stack))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'existing audio')

    class InteractiveInput(StringIO):
        def isatty(self):
            return True

    prompts = []
    def approve(prompt):
        prompts.append(prompt)
        return 'yes'

    monkeypatch.setattr(sys, 'stdin', InteractiveInput())
    monkeypatch.setattr('builtins.input', approve)

    assert not track.check_skippable(stack)
    assert path.read_bytes() == b'existing audio'
    assert len(prompts) == 1
    assert 'numbered copy' in prompts[0]


def test_numbered_copy_requires_explicit_yes_and_is_scoped_to_track(tmp_path):
    path = tmp_path / 'Artist - Song.mp3'
    no_prompt = Mock()
    assert not request_suffixed_download_approval(
        path, 'track-a', 'Artist - Song', is_interactive=False, input_fn=no_prompt)
    no_prompt.assert_not_called()

    yes_input = Mock(return_value=' YES ')
    assert request_suffixed_download_approval(
        path, 'track-a', 'Artist - Song', is_interactive=True, input_fn=yes_input)
    yes_input.assert_called_once()
    already_approved = Mock(side_effect=AssertionError('approval should be cached'))
    assert request_suffixed_download_approval(
        path, 'track-a', 'Artist - Song', is_interactive=True, input_fn=already_approved)
    already_approved.assert_not_called()

    no_input = Mock(return_value='no')
    assert not request_suffixed_download_approval(
        path, 'track-b', 'Artist - Song', is_interactive=True, input_fn=no_input)
    no_input.assert_called_once()
    already_denied = Mock(side_effect=AssertionError('denial should be cached'))
    assert not request_suffixed_download_approval(
        path, 'track-b', 'Artist - Song', is_interactive=True, input_fn=already_denied)
    already_denied.assert_not_called()
