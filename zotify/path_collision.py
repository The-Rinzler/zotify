"""Fail-closed confirmation for unarchived output-path collisions."""

from collections.abc import Callable
import os
from pathlib import Path
import sys


_collision_decisions: dict[tuple[Path, str], bool] = {}


def request_suffixed_download_approval(
        path: str | os.PathLike[str], track_id: str, track_name: str,
        *, is_interactive: bool | None = None,
        input_fn: Callable[[str], str] | None = None) -> bool:
    """Return True only when this track's numbered duplicate was approved."""
    target = Path(path)
    collision = (target, str(track_id))
    if collision in _collision_decisions:
        return _collision_decisions[collision]

    if is_interactive is None:
        is_interactive = sys.stdin.isatty()
    if not is_interactive:
        return False

    if input_fn is None:
        input_fn = input
    prompt = (
        f'An unarchived file already exists at "{target}" for "{track_name}" '
        f'(track ID {track_id}). Download a numbered copy? [y/N] '
    )
    try:
        approved = input_fn(prompt).strip().lower() in {"y", "yes"}
    except (EOFError, OSError):
        return False

    _collision_decisions[collision] = approved
    return approved
