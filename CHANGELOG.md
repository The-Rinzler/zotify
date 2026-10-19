# Changelog

Changes listed here are for the personal macOS compatibility fork, not an
independent upstream version history. The package version remains `0.21.0`.

## Unreleased — macOS release preparation

### Added
- Project-local macOS venv bootstrap (`scripts/setup_macos.sh`), opt-in offline
  tests, guarded `--update`, explicit interpreter selection, and isolation from
  global `PYTHONPATH`/`PYTHONHOME`.
- macOS installation, manual `.zshrc` aliases, authentication/Developer API key
  guidance, and configuration reference.
- Disposable setup-script safety tests; no real Spotify login is required.

### Changed
- README now describes this personal fork and its shared contract with
  Zotify-MacOS-Music-Manager rather than upstream's cross-platform install flow.
- Inherited mirror-push workflow disabled: merging personal PRs must never push
  to the original project's repositories.
- Ignore rules expanded for credential caches, private environment files,
  archives and generated audio/playlist files.

### Verification boundary
- Offline tests and fresh-install checks are supplemental preflight. Native
  macOS installation, live OAuth/API access and one real download still require
  acceptance on the Mac; no live-auth fix is claimed by documentation changes.

## v0.21.0 compatibility baseline

Based on Googolplexed0/zotify `v0.21.0`
(`e21821bb58521cb7590b73b7a2768de868afe8c0`), with the existing personal overlay:

- MP3/auto-quality defaults, first-artist filenames, flat playlist directories,
  and physical copies for repeated playlist memberships in both download modes.
- Preserve legacy sanitizer behavior, guard exact `.`/`..` path components,
  and prevent archived non-MP3 files from masquerading as successful MP3s.
- Five-column `.song_ids` compatible with the manager; upstream six-column global
  archives supported, including stale/repeated-ID lookup and appended records.
- Pin librespot-python to `01abfc8ad012dbc40e90417e640faaf271ea2f98`.
- Synthetic-audio/metadata/archive/M3U8 regression tests and opt-in integration
  with the actual companion manager, including native Vorbis encoder fallback.

See [MIGRATION-v0.21.0.md](MIGRATION-v0.21.0.md) for compatibility details and rollback.
