"""The legacy sanitizer is a persisted Music.app/iPod filename contract."""
import pytest
from zotify.api import Content


@pytest.mark.parametrize(("raw", "expected"), [
    ('AC/DC #1: "Wow"!*?\\', 'AC_DC _1_ "Wow"_*_\\'),
    (' leading and trailing . ', ' leading and trailing . '),
    ('CON', '_'), ('aux.mp3', '_.mp3'), ('COM0', 'COM0'),
    ('CONcert', 'CONcert'), ('AUX - NUL', 'AUX - NUL'),
    ('Björk — Café e\u0301', 'Björk — Café e\u0301'),
    ('a\x00b\x1fc\x7f', 'a_b_c\x7f'),
])
def test_legacy_sanitizer(raw, expected):
    assert Content.fix_filename(raw) == expected


def test_sanitizer_matches_real_manager(manager_modules):
    manager_utils, _, _ = manager_modules
    samples = [chr(i) for i in range(128)]
    samples += [f'{artist} - {title}' for artist in ('CON', 'AUX', 'Artist#', 'Björk')
                for title in ('NUL', 'Wow!*?', '"Hello"', ' Back\\slash. ')]
    for name in samples:
        assert Content.fix_filename(name) == manager_utils.sanitize_filename(name)
