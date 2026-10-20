# Zotify — macOS / Music.app / iPod edition

Personal macOS fork: [The-Rinzler/zotify](https://github.com/The-Rinzler/zotify), based on **Googolplexed0 Zotify v0.21.0** with a compatibility overlay for the [Zotify-MacOS-Music-Manager](https://github.com/The-Rinzler/Zotify-MacOS-Music-Manager). The Python package version remains `0.21.0`; use the Git commit to identify this fork.

**macOS is the target.** This is not an Apple or Spotify product. Use it only for content you are authorized to access and download. Account access, API availability, and service terms can change; uninterrupted service is not guaranteed.

## What this fork preserves

- MP3 output selected by configuration; `auto` requests the highest source quality available to the account (upstream selection: Premium `320k`, otherwise `160k`). Re-encoding does not improve the original lossy source.
- Flat playlist folders and `First Artist - Title.mp3` names; additional artists remain in metadata. A track in two playlists has a physical copy in each.
- The existing macOS filename substitutions and five-column directory `.song_ids`. The global `.song_archive` can contain the upstream sixth ISRC field.
- Upstream metadata, M3U8 playlists, lyrics, search, albums, artists, liked songs, and podcasts. The manager builds the Consolidated Library separately; it does not require Zotify to move or delete playlist originals.

Start here: [macOS installation](INSTALLATION.md) · [Authentication and keys](docs/AUTHENTICATION.md) · [Configuration reference](docs/CONFIGURATION.md) · [Deployment and compatibility](MIGRATION-v0.21.0.md) · [Changelog](CHANGELOG.md)

## Install on macOS

Install [Homebrew](https://brew.sh/) if needed, then run in Terminal:

```zsh
brew install python@3.11 ffmpeg git && \
  git clone --branch compat/macos-ipod-v0.21.0 https://github.com/The-Rinzler/zotify.git "$HOME/zotify" && \
  cd "$HOME/zotify" && \
  PYTHON="$(brew --prefix python@3.11)/bin/python3.11" bash scripts/setup_macos.sh --test
```

If `~/zotify` already exists, don't clone over it; use the update procedure below
or choose a different empty path. If `git clone` fails, stop instead of continuing
with `cd` or setup commands. Python 3.11 is recommended (Python 3.10+ is
required). Both `ffmpeg` and `ffprobe` must be on `PATH`; use an FFmpeg build with
an MP3 encoder such as `libmp3lame`.

The script creates a project-local `.venv`, installs this checkout (not a similarly named PyPI package), checks dependencies and CLI startup, and does not install Homebrew, sign in to Spotify, edit `.zshrc`, or overwrite another environment/configuration/library. It clears inherited `PYTHONPATH` and `PYTHONHOME` during setup. `--update` is only for a venv created by this script in this exact checkout; it reinstalls the checked-out source and dependencies but does not pull Git changes or migrate credentials.

## Update an existing checkout

First confirm this is the Zotify checkout, that `origin` is the expected fork,
and that the working tree has no uncommitted changes. If it is dirty, stop and
preserve those changes before updating:

```zsh
cd "$HOME/zotify" && \
  git status --short --branch && \
  git remote get-url origin
```

After confirming the remote is `https://github.com/The-Rinzler/zotify.git` and
the checkout is clean, fast-forward the compatibility branch and refresh the
venv:

```zsh
git fetch origin && \
  git switch compat/macos-ipod-v0.21.0 && \
  git pull --ff-only origin compat/macos-ipod-v0.21.0 && \
  PYTHON="$(brew --prefix python@3.11)/bin/python3.11" bash scripts/setup_macos.sh --update --test
```

Git updates the source; `setup_macos.sh --update` reinstalls that source and its
dependencies. It does not migrate config or credentials, change shell files, or
touch downloaded music. If setup refuses the existing venv, don't remove its
guard or point it at another environment; use a separate checkout and follow
[INSTALLATION.md](INSTALLATION.md).

## Add a zsh alias

Use a distinct alias so an existing `zotify` command or playlist wrapper stays available. Back up `~/.zshrc`, add the following line manually, then reload and confirm it resolves to the new environment:

```zsh
alias zotify_mac='env -u PYTHONPATH -u PYTHONHOME "$HOME/zotify/.venv/bin/zotify"'
```

Then reload and confirm it resolves to the new environment:

```zsh
source ~/.zshrc
type -a zotify_mac
zotify_mac --version
```

If you choose to replace an existing `zotify` alias/function, inspect it first and keep a rollback path. Setup never edits your shell files.

## First launch and regular use

Zotify creates its default configuration on first launch under `~/Library/Application Support/Zotify/` and saves credentials there after successful browser authorization. The default music and podcast destinations are `~/Music/Zotify Music` and `~/Music/Zotify Podcasts`; review or change these values in `config.json` before a larger download. See [Authentication](docs/AUTHENTICATION.md) for the browser sign-in flow and optional Developer API app.

Start with one specific item you are authorized to download, then use the same command pattern for your intended content:

```zsh
zotify_mac 'https://open.spotify.com/track/TRACK_ID'
zotify_mac 'https://open.spotify.com/playlist/PLAYLIST_ID'
zotify_mac --playlist
zotify_mac --liked
zotify_mac --help
```

Pass `--root-path` or `--root-podcast-path` if you need to select a destination for a command. On macOS, omitting `--config-location` uses `~/Library/Application Support/Zotify/config.json`; alternate config locations are not sticky, so specify them on every invocation. Existing config settings take precedence over fork defaults unless overridden on the CLI. Replace deprecated `OUTPUT_PLAYLIST` with `OUTPUT_PLAYLIST_EXT`. Enable M3U8 export in JSON with `"EXPORT_M3U8": true`; the inherited upstream export CLI flag is malformed. Avoid `--verify-library` unless you intend to update audio metadata.

## License and credits

[Unlicense](LICENSE). Thanks to the original Zotify contributors, Googolplexed0, and librespot-python contributors. The streaming fork is pinned to commit `01abfc8ad012dbc40e90417e640faaf271ea2f98`; see `pyproject.toml`.