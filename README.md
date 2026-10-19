# Zotify — macOS / Music.app / iPod edition

Personal fork: [The-Rinzler/zotify](https://github.com/The-Rinzler/zotify).
Based on **Googolplexed0 Zotify v0.21.0**, with a compatibility overlay for the
[Zotify-MacOS-Music-Manager](https://github.com/The-Rinzler/Zotify-MacOS-Music-Manager).
The Python package version remains `0.21.0`; use the Git commit to identify this fork.

**macOS is the target.** This is not an Apple or Spotify product. Only download
content you are authorized to download; account access, API availability and
service terms can change. No account-safety or uninterrupted-service guarantee is made.

## What this fork preserves

- Configuration-selected MP3; `auto` requests the account's highest supported
  source quality (upstream selection: Premium `320k`, otherwise `160k`).
  Re-encoding does not improve the original lossy source.
- Flat playlist folders and `First Artist - Title.mp3` names; additional artists
  remain in metadata. A track in two playlists has a **physical copy in each**.
- The existing macOS filename substitutions and five-column directory `.song_ids`.
  The global `.song_archive` can contain the upstream sixth ISRC field.
- Metadata, M3U8 playlists, lyrics, search, albums, artists, liked songs and podcasts
  from upstream. The manager separately builds the Consolidated Library—it does
  not require Zotify to move or delete playlist originals.

Start here:
[macOS installation](INSTALLATION.md) · [Authentication and keys](docs/AUTHENTICATION.md) ·
[Configuration reference](docs/CONFIGURATION.md) · [Changelog](CHANGELOG.md) ·
[Migration and compatibility details](MIGRATION-v0.21.0.md)

## Quick setup on macOS

Install [Homebrew](https://brew.sh/) if needed, then run in Terminal:

```zsh
brew install python@3.11 ffmpeg git
git clone --branch compat/macos-ipod-v0.21.0 https://github.com/The-Rinzler/zotify.git "$HOME/zotify"
cd "$HOME/zotify"
PYTHON="$(brew --prefix python@3.11)/bin/python3.11" bash scripts/setup_macos.sh --test
```

Use a **new clone directory** if `~/zotify` already exists. While reviewing an
unmerged PR, check out that PR's branch before running setup: older default or
compatibility branches may not yet contain these scripts.

The script creates only **this checkout's `.venv`**, installs this source (not
PyPI's similarly named package), checks dependencies and the CLI, and optionally
runs offline tests. It clears `PYTHONPATH`/`PYTHONHOME` while setting up. It never
installs Homebrew, runs Spotify login, changes `.zshrc`, or overwrites another
venv/config/music folder. Python 3.11 is recommended; the project requires 3.10+.
Both `ffmpeg` and `ffprobe` must be on PATH. Use an FFmpeg build with an MP3 encoder
such as `libmp3lame`.

If `.venv` already exists, setup stops. `bash scripts/setup_macos.sh --update --test`
permits reuse **only when the venv was created by this script in this exact checkout**.
It does not pull Git updates or upgrade production credentials. Dependencies are
not fully locked; reinstalling later can select newer compatible PyPI versions.

### Add a `.zshrc` alias

First inspect existing commands (`type -a zotify zotify_playlist`). Back up
`~/.zshrc` before editing it; keep existing aliases/functions until acceptance tests
pass. Add this line manually, adapting the checkout path if necessary:

```zsh
alias zotify='env -u PYTHONPATH -u PYTHONHOME "$HOME/zotify/.venv/bin/zotify"'
```

Then `source ~/.zshrc`, followed by `type -a zotify` and `zotify --version`.
If a function named `zotify` already exists, replace or rename it deliberately;
adding an alias is not a migration of an old `zotify_playlist` wrapper. See
[installation](INSTALLATION.md) for separate-manager aliases and rollback.

## First run: authenticate in an isolated test root

Zotify has **Login5 streaming credentials** and an optional, separate **Developer
API OAuth identity**. A Client ID is not a Login5 token; the manager's Client
Secret is not used here. Follow [Authentication](docs/AUTHENTICATION.md) first.

```zsh
cd "$HOME/zotify"
TEST="$(mktemp -d "$HOME/zotify-smoke.XXXXXX")"
chmod 700 "$TEST"
mkdir -p "$TEST/config"
cp examples/config.macos-ipod.json "$TEST/config/config.json"
# Preserve these explicit paths on EVERY test invocation.
zotify_smoke() {
  env -u PYTHONPATH -u PYTHONHOME "$HOME/zotify/.venv/bin/zotify" \
    --config-location "$TEST/config" \
    --credentials-location "$TEST/login5.json" \
    --api-credentials-location "$TEST/devapi.json" \
    --root-path "$TEST/music" --root-podcast-path "$TEST/podcasts" \
    --song-archive-location "$TEST/.song_archive" "$@"
}
zotify_smoke --test 'PASTE_ONE_SMALL_PLAYLIST_URL'
```

Replace the placeholder. `--test` avoids audio downloads but **still logs in and
may write test configuration/caches and query Spotify**. A created credential
file is not proof of a successful session. Do not delete production caches to fix
a test failure. Stop on authentication errors or HTTP 429; see the auth guide.
After a successful query, repeat without `--test` for a deliberate small download.
Check the real codec/bitrate with FFprobe and overlapping playlist copies before
cutover; the [migration checklist](MIGRATION-v0.21.0.md#mac-acceptance-isolated-config-credentials-and-library)
has the acceptance procedure.

## Regular usage

After deliberately selecting your production config and completing acceptance:

```zsh
zotify --config-location '/absolute/path/to/config' 'https://open.spotify.com/playlist/PLAYLIST_ID'
zotify --config-location '/absolute/path/to/config' --playlist
zotify --config-location '/absolute/path/to/config' --liked
zotify --help
```

On macOS, omitting `--config-location` uses
`~/Library/Application Support/Zotify/config.json`. Alternate config locations
are **not sticky**: specify them every time. Existing config settings take
precedence over fork defaults unless overridden on the CLI. Migrate deprecated
`OUTPUT_PLAYLIST` to `OUTPUT_PLAYLIST_EXT`. Set `"EXPORT_M3U8": true` in JSON:
upstream's export CLI flag is malformed, so this guide does not depend on it.
Avoid `--verify-library` during a smoke test: it updates audio metadata.

## Verification and release boundary

```zsh
cd "$HOME/zotify"
env -u PYTHONPATH -u PYTHONHOME .venv/bin/python -m pytest tests -q
```

`setup_macos.sh --test` installs pytest. Tests forbid network access and use
synthetic audio—not a Spotify stream. Two cross-repository tests are opt-in:
install the manager's requirements into a disposable test environment, then set
`ZOTIFY_MANAGER_SOURCE` to its checkout when running pytest. Do not treat their
expected skips in the standalone environment as proof of manager integration.

The new setup orchestration has disposable shell-harness tests; Linux preflight
is supplemental. **Native macOS setup, browser authorization and a live download
remain acceptance checks on the Mac**, not inferred from offline tests. No
production environment, account cache or music library needs to be changed to
review this release.

## License and credits

[Unlicense](LICENSE). Thanks to the original Zotify contributors, Googolplexed0,
and librespot-python contributors. The streaming fork is pinned to commit
`01abfc8ad012dbc40e90417e640faaf271ea2f98`; see `pyproject.toml`.
