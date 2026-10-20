# Deployment and compatibility notes — Zotify v0.21.0

This is the macOS compatibility fork based on the full **Googolplexed0/zotify v0.21.0** codebase, not the earlier 0.15.3 source with a changed version string. The personal repository is [The-Rinzler/zotify](https://github.com/The-Rinzler/zotify), and its deployment branch is `compat/macos-ipod-v0.21.0`. Package metadata remains `0.21.0`; use the Git commit to distinguish fork revisions.

| Component | Source |
| --- | --- |
| Upstream base | `https://github.com/Googolplexed0/zotify`, tag `v0.21.0`, commit `e21821bb58521cb7590b73b7a2768de868afe8c0` |
| Personal fork | `https://github.com/The-Rinzler/zotify`, branch `compat/macos-ipod-v0.21.0` |
| Streaming dependency | `https://github.com/Googolplexed0/librespot-python`, pinned commit `01abfc8ad012dbc40e90417e640faaf271ea2f98` |
| Companion manager | [Zotify-MacOS-Music-Manager](https://github.com/The-Rinzler/Zotify-MacOS-Music-Manager) |

The streaming dependency is pinned to prevent a moving upstream branch from silently changing this release. Other PyPI dependencies retain their declared version constraints and are not fully locked.

## Preserved data contract

- Track filenames are `{first artist} - {title}.mp3`. Additional artists remain in ID3 metadata, not the filename.
- Output is MP3 selected by configuration and defaults to the highest source quality supported by the authenticated account. Upstream v0.21.0 maps `auto` to very-high / `320k` for Premium or high / `160k` otherwise. Re-encoding cannot improve the original lossy stream; review and preserve deliberate bitrate overrides during cutover.
- Each playlist has a flat directory. A track in two playlists has a physical copy in each; a global archive entry alone must not suppress the second membership.
- The manager, not Zotify, separately constructs a flat Consolidated Library. Zotify does not move, rename, or delete playlist originals to consolidate them.
- The legacy macOS filename substitution is preserved: `/ # : | < > ! ?` and control characters are replaced. Quotes, asterisks, backslashes, leading/trailing spaces, and trailing dots remain untouched; reserved device-name substitution is case-insensitive. This is the prior macOS contract, not Windows-safe normalization.
- Apply substitution to each fully assembled path component, not to artist/title fragments separately. A slash in metadata becomes `_`, not a directory; a template's `/` still separates directories. Exact `.` and `..` components are rejected before path construction, with unsafe upstream paths falling back to an ID-based filename under the configured root. Podcast show-directory construction applies the same boundary guard.
- Directory `.song_ids` rows have exactly five TSV fields: ID, timestamp, artist, title, and relative path/basename. Tabs and newlines in metadata are flattened to spaces.
- The global `.song_archive` retains the upstream sixth ISRC field. Its reader accepts legacy five-column and upstream six-column entries; existing archives are not bulk-rewritten on installation. Missing/empty archive paths and repeated IDs are handled without suppressing a usable later entry.
- A matching-format archive item can provide a physical copy in another requested playlist; an archived OGG cannot stand in for an MP3. Failed MP3 conversion does not mark an OGG fallback as a successful MP3 download.

## Deploy on macOS

Use a new checkout and its own venv. Keep any previous checkout, venv, config, account cache, and music library in place until you have deliberately switched your workflow:

```zsh
brew install python@3.11 ffmpeg git
git clone --branch compat/macos-ipod-v0.21.0 https://github.com/The-Rinzler/zotify.git "$HOME/zotify"
cd "$HOME/zotify"
PYTHON="$(brew --prefix python@3.11)/bin/python3.11" bash scripts/setup_macos.sh
"$HOME/zotify/.venv/bin/zotify" --version
```

See [INSTALLATION.md](INSTALLATION.md) for prerequisites, the `.zshrc` alias, updates, and rollback. See [Authentication](docs/AUTHENTICATION.md) for first-run browser authorization and optional Developer API setup.

On macOS, `config.json` and credentials saved after successful authorization are under `~/Library/Application Support/Zotify/` by default. Default output directories are `~/Music/Zotify Music` and `~/Music/Zotify Podcasts`. Review `config.json` and its output paths before a large download. Existing configs take precedence over code defaults. Replace deprecated `OUTPUT_PLAYLIST` with `OUTPUT_PLAYLIST_EXT`; do not overwrite existing credentials without checking their format and keeping a private backup.

Start with one intended item and confirm it lands in the expected output directory. Then invoke the desired playlist, album, artist, or other command normally. Existing playlist files are not changed by installation, but downloads and library verification can write or update files according to the active config.

## Updating and rollback

For an existing checkout on the personal fork's deployment branch:

```zsh
cd "$HOME/zotify"
git fetch origin
git pull --ff-only origin compat/macos-ipod-v0.21.0
PYTHON="$(brew --prefix python@3.11)/bin/python3.11" bash scripts/setup_macos.sh --update
```

The update option only recognizes a venv created by this setup script in this checkout. It reinstalls the selected source; it does not pull Git changes, move libraries, or migrate account credentials. Inspect the reviewed commit before updating and keep the previous executable/configuration available.

To roll back, point your alias or command back to the previous executable and restore the previous config backup if needed. Do not delete music, archives, or account files as a rollback step. The manager has a separate venv and deployment procedure.

## Licensing and provenance

The source repository carries the [Unlicense](LICENSE). This fork retains the upstream v0.21.0 package version and credits; release notes are in [CHANGELOG.md](CHANGELOG.md).