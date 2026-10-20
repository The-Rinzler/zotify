# Changelog

Changes listed here describe the personal macOS compatibility fork, not an independent upstream version history. The Python package version remains `0.21.0`.

## Unreleased — deployment guide refresh

### Added
- Project-local macOS venv setup with explicit interpreter selection, guarded `--update`, dependency checks, and isolation from inherited `PYTHONPATH`/`PYTHONHOME`.
- macOS installation, `.zshrc` alias, authentication/Developer API, and configuration guides.

### Changed
- Updated README and macOS deployment/authentication/migration guides for direct installation, first-run sign-in, production paths, updates, and rollback.
- Updated deployment instructions to use the personal fork's current `compat/macos-ipod` branch and a distinct `.zshrc` alias.
- Disabled the inherited mirror-push workflow so personal changes cannot be pushed to the upstream project.
- Expanded ignore rules for credential caches, private environment files, archives, and generated audio/playlist files.

### Fixed
- Treat playlist entry `is_local` flags as authoritative for local detection and skip local tracks before metadata requests or output-path/archive checks.

## v0.21.0 compatibility baseline

Based on Googolplexed0/zotify `v0.21.0` (`e21821bb58521cb7590b73b7a2768de868afe8c0`), with the existing personal overlay:

- MP3/auto-quality defaults, first-artist filenames, flat playlist directories, and physical copies for repeated playlist memberships in both download modes.
- Preserve legacy filename substitutions, guard exact `.`/`..` path components, and prevent archived non-MP3 files from masquerading as successful MP3s.
- Five-column `.song_ids` compatible with the manager; upstream six-column global archives are supported, including stale/repeated-ID lookup and appended records.
- Pin librespot-python to `01abfc8ad012dbc40e90417e640faaf271ea2f98`.

See [Deployment and compatibility notes](MIGRATION-v0.21.0.md) for the data contract and update/rollback procedure.