# Zotify v0.21.0 — macOS / Music.app / iPod compatibility migration

## Scope and provenance

This is **the full Googolplexed0/zotify v0.21.0 codebase**, with a small compatibility overlay. It is not the old 0.15.3 code with a changed version string.

This is maintained on **your own branch for your personal GitHub repository**, `https://github.com/The-Rinzler/zotify.git`. In the migration worktree, `origin` is that personal repository and `upstream` is Googolplexed0. Googolplexed0 supplies the upstream base only: do not push this compatibility work there. Nothing has been pushed by this migration. Native **macOS is the acceptance-test target**; Linux checks below are supplemental offline preflight, not a replacement for Mac testing.

| Component | Exact source |
| --- | --- |
| Upstream base | `https://github.com/Googolplexed0/zotify`, tag `v0.21.0`, commit `e21821bb58521cb7590b73b7a2768de868afe8c0` |
| Migration branch | `compat/macos-ipod-v0.21.0`, separate worktree `/home/hermes/shared/zotify-v0.21.0` |
| Legacy contract baseline | `/home/hermes/shared/zotify`, branch `compat/macos-ipod`, `41da6e59ca3a97c006cf7cd233db1abcfbbf0d22` — unchanged |
| Streaming dependency | `https://github.com/Googolplexed0/librespot-python`, pinned `01abfc8ad012dbc40e90417e640faaf271ea2f98` |
| Manager contract | `/home/hermes/shared/zotify-macos-music-manager`, HEAD `615baef458b85e5a0db7eaa30247a6c8d3430b93` plus its existing uncommitted changes — unchanged |

The dependency pin prevents a future `main` change from silently changing this migration. Other upstream PyPI dependencies retain their original constraints; this is not a fully locked environment.

## Preserved data contract

- Track filenames: **`{first artist} - {title}.mp3`**. Additional artists remain in ID3 metadata, not the filename.
- Audio remains **MP3 selected by config**, at the highest source quality supported by the authenticated account. The sample explicitly sets `DOWNLOAD_FORMAT: mp3`, `DOWNLOAD_QUALITY: auto`, and `TRANSCODE_BITRATE: auto`. In upstream v0.21.0, `auto` selects very-high / `320k` for Premium or high / `160k` otherwise; auto transcoding uses that selected bitrate. Re-encoding cannot improve the original lossy stream. Existing production MP3/bitrate settings are not overwritten; review and preserve deliberate overrides during cutover.
- Each playlist has a flat directory. A track belonging to two playlists has a physical MP3 copy in each. A global archive entry alone must not suppress the second membership.
- The manager, not Zotify, separately constructs a flat **Consolidated Library**. Zotify does not move, rename, or delete playlist originals to consolidate them.
- Legacy filename substitution is preserved, including replacing `/ # : | < > ! ?` and control characters. Quotes, asterisks, backslashes, leading/trailing spaces, and trailing dots remain untouched. Reserved device-name substitution is case-insensitive. This is intentionally the old macOS contract, **not Windows-safe filename normalization**.
- Apply substitution to each fully assembled path component, not to artist/title fragments separately. A slash inside metadata becomes `_`, not a directory. A template's `/` still separates directories. Exact `.`/`..` components are rejected before path construction; upstream's error handler falls back to an ID-based file under the configured root instead of escaping the library. Podcast show-directory construction applies the same boundary guard without changing the legacy sanitizer.
- Directory `.song_ids` records have exactly **five TSV fields**: `ID`, `timestamp`, `artist`, `title`, `relative path/basename`. Tabs/newlines in metadata are flattened to spaces to prevent malformed records.
- Global `.song_archive` keeps upstream's sixth ISRC field. The reader accepts legacy five-column and upstream six-column entries. Writes/updates of directory archives normalize them to five columns; existing archives are not bulk-rewritten on installation.

## Compatibility overlay

- `zotify/config.py`: MP3 and legacy filename/layout defaults; existing settings can still override defaults. **Do not reuse the old config blindly**: upstream `OUTPUT_PLAYLIST` is deprecated; use `OUTPUT_PLAYLIST_EXT`.
- `zotify/api.py`: legacy sanitizer; assemble path components before sanitizing; preserve every playlist destination in both download modes. A matching-format global archive entry can supply a physical copy even when its original playlist is not requested in this run; enabling global skipping must not suppress a new playlist membership, and an archived OGG cannot stand in for an MP3. MP3 conversion failure retains the temporary source and does not mark an OGG fallback as successfully downloaded.
- `zotify/metadata.py`: five-column directory schema versus six-column global schema; append subsequent records; preserve empty TSV fields; ignore missing/empty archive paths and find a usable later entry when IDs repeat.
- `pyproject.toml`: pin the streaming dependency. Package version remains `0.21.0`.
- `tests/`: offline regression and real FFmpeg/ID3/manager integration tests.
- `examples/config.macos-ipod.json`: safe test-root configuration, never production credential paths.

All other upstream architecture, including the v0.21.0 Login5/DevAPI credential split, is retained. Installing or importing this code does **not** prove Spotify authentication works.

## Automated verification (Linux)

Python >=3.10, FFmpeg and FFprobe are required. Run from this source tree after installing the package and pytest into an isolated venv:

```sh
env -u PYTHONPATH -u PYTHONHOME /path/to/venv/bin/python -m pytest tests -q
```

The cross-repository tests additionally require the manager's Python dependencies and an explicit source path:

```sh
env -u PYTHONPATH -u PYTHONHOME \
  ZOTIFY_MANAGER_SOURCE=/home/hermes/shared/zotify-macos-music-manager \
  /path/to/venv/bin/python -m pytest tests -q
```

Tests forbid socket connections. They generate a short synthetic sine tone, exercise real MP3 transcoding, ID3 tagging, archive writes, M3U8 generation and playlist copies, and invoke the **actual manager's** archive cleanup and consolidation on disposable fixtures. This is not a Spotify stream or evidence of a live download. No manager source is modified.

## Mac install: separate venv, no production changes

Your earlier output showed the **old** environment: `Zotify 0.15.3`, imported from `~/zotify-macos-test.I4NtRj/zotify`. Keep it intact. The new archive/source below is a separate install.

1. Extract the provided `zotify-v0.21.0-macos-ipod.tar.gz` into your home directory. It contains a `zotify-v0.21.0-macos-ipod` folder. Do not overwrite an existing folder with that name.
2. From outside the old checkout, use a new venv. Python 3.11 is a conservative choice. If FFmpeg/FFprobe are absent, install them first (e.g. `brew install ffmpeg`).

```sh
cd "$HOME"
unset PYTHONPATH PYTHONHOME
SRC="$HOME/zotify-v0.21.0-macos-ipod"
VENV="$HOME/venvs/zotify-v0.21.0-compat"
# Run the following only if this venv path does not already exist.
python3.11 -m venv "$VENV"
"$VENV/bin/python" -m pip install "$SRC"
"$VENV/bin/python" -m pip check
"$VENV/bin/zotify" --version
"$VENV/bin/python" -c 'import sys,zotify.config; from importlib.metadata import version; print(sys.executable); print(zotify.config.__file__); print(version("zotify"))'
"$VENV/bin/zotify" --help
ffmpeg -version
ffprobe -version
```

Expect `Zotify 0.21.0`; the `zotify.config` import must resolve inside the new venv, **not** to `zotify-macos-test.I4NtRj`. Upstream v0.21.0 uses a namespace package, so bare `zotify.__file__` can be `None`; inspect `zotify.config.__file__` instead. Using `python -m zotify` while standing inside the old checkout can shadow the new installation, so keep `cd "$HOME"`. No activation, alias change, uninstall, or production credential migration is needed.

## Mac acceptance: isolated config, credentials and library

Create a fresh test directory and copy the sample config:

```sh
TEST="$(mktemp -d "$HOME/zotify-v021-smoke.XXXXXX")"
mkdir -p "$TEST/config" "$TEST/music" "$TEST/podcasts"
cp "$SRC/examples/config.macos-ipod.json" "$TEST/config/config.json"
```

Use **all** these isolation options on **every** test invocation; omitting them can select the default macOS config/credentials:

```sh
"$VENV/bin/zotify" \
  --config-location "$TEST/config" \
  --credentials-location "$TEST/login5.json" \
  --api-credentials-location "$TEST/devapi.json" \
  --root-path "$TEST/music" \
  --root-podcast-path "$TEST/podcasts" \
  --song-archive-location "$TEST/.song_archive" \
  --test 'PASTE_ONE_SMALL_PLAYLIST_URL_HERE'
```

Replace the placeholder before running. `--test` avoids downloads but still requires live Spotify authentication/API access. Complete OAuth in the browser yourself; never paste credentials or tokens into chat.

- v0.21.0 distinguishes Login5 credentials from optional custom DevAPI OAuth credentials. Do not copy one credential file into the other.
- A custom DevAPI client is optional. If your setup requires it, configure your own `--client-id` and `--client-legacy False`; register the exact upstream callback `http://127.0.0.1:4381/login` in that app. These options do not replace the separate Login5 OAuth identity.
- A saved credential file or an opened login page is **not** proof of successful login. Require a successful authenticated query.
- If Spotify reports `client_id: Invalid`, Login5 invalid credentials, or HTTP 429, stop and retain the redacted error for diagnosis. A 429 is rate limiting, not an empty playlist. Do not delete production caches or repeatedly retry.

After the authenticated dry-run succeeds, repeat the same command **without `--test`** for one small playlist, then a second containing an overlapping track. This is a deliberate real download, restricted to `$TEST/music`.

Confirm:

1. Each playlist folder contains flat `First Artist - Title.mp3` names with the legacy character substitutions.
2. Overlapping tracks exist in **both** playlist folders; `.song_ids` has exactly five fields per line, with a valid basename in field 5.
3. Re-running creates no numbered duplicates, does not drop archive rows and does not re-download intact indexed tracks.
4. M3U8 entries point to existing files. Enable via the sample config's `EXPORT_M3U8`; the unmodified upstream v0.21.0 CLI's export option contains a typo, so do not depend on `--export-m3u8`.
5. Only after these checks, run the manager against the **test root**, with its destination set to a separate test `Consolidated Library` outside the scanned source. Preview destructive actions first. Confirm one flat consolidated MP3 per filename and unchanged playlist originals. Do not run its cleanup against the production library as a smoke test.

Check the real Mac output codec and bitrate as well, replacing the placeholder with one downloaded test file:

```sh
ffprobe -v error -select_streams a:0 \
  -show_entries stream=codec_name,bit_rate -of default=noprint_wrappers=1 \
  '/absolute/path/to/test/First Artist - Title.mp3'
```

Require `codec_name=mp3` and a bitrate consistent with the account-supported quality selected at login. A `.mp3` extension alone does not verify encoding. Do not force `copy` or retain OGG files as successful MP3 downloads.

## Cutover and rollback

This migration does **not** replace the production checkout, shell function/alias, venv, config, credentials or library. After Mac acceptance, a separate deliberate cutover can point your existing workflow at the new venv and compatible config. Back up config/archives first; do not mix old and new credential formats.

To roll back the test, simply stop using the new venv and return to the old `zotify-macos-test`/production environment. Keep or remove only the explicitly created test source, venv and `$TEST` directory once no longer needed. No rollback of the manager or production music is required because they were never changed.

## Verification boundary

Linux automated tests and fresh-install checks are executable here. Native macOS behavior, Spotify browser authorization, post-login API access and a real Spotify download require the Mac acceptance steps above; none should be inferred from an offline fixture test. Snyk cloud scanning is not claimed: uploading private source requires separate permission/authentication.
