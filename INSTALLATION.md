# macOS installation and updates

This guide installs **this fork's source** in a project-local `.venv`. Keep any
existing Zotify venv, production checkout and aliases until the Mac acceptance
tests in the [migration guide](MIGRATION-v0.21.0.md) pass.

## 1. Prerequisites

Install Homebrew using the instructions at <https://brew.sh/>, if needed. Then:

```zsh
brew install python@3.11 git ffmpeg
command -v ffmpeg ffprobe
ffmpeg -version
ffprobe -version
ffmpeg -hide_banner -encoders 2>/dev/null | /usr/bin/grep libmp3lame
```

The MP3 path needs a working MP3 encoder; the stock Homebrew FFmpeg is the
recommended starting point. Python 3.11 is recommended (project minimum 3.10).
Do not use `sudo pip`, system Python, or a venv belonging to the old release.

## 2. Clone the personal fork and create the venv

```zsh
git clone --branch compat/macos-ipod-v0.21.0 https://github.com/The-Rinzler/zotify.git "$HOME/zotify"
cd "$HOME/zotify"
PYTHON="$(brew --prefix python@3.11)/bin/python3.11" bash scripts/setup_macos.sh --test
```

If `~/zotify` exists, choose a different empty destination and adapt every path in
this guide. For an unmerged review PR, check out its head branch first; the base
branch may not contain setup yet. `bash scripts/setup_macos.sh --help` lists flags.

The script resolves paths relative to itself (paths with spaces work), clears
`PYTHONPATH` and `PYTHONHOME`, refuses existing `.venv`s by default, installs this
checkout, checks dependencies and CLI startup, and optionally runs offline tests.
It does **not** log in, install Homebrew, edit shell files, or touch user data.
Downloads/builds during pip installation need network access. The streaming
library is pinned in `pyproject.toml`, but PyPI dependencies are not fully locked.

If setup fails after creating `.venv`, keep its error. Fix the prerequisite and
rerun with `--update`; an interrupted venv creation before its marker was written
is deliberately not recognized. Move only that newly created test `.venv` aside
and retry, rather than pointing setup at an old production environment.

## 3. Verify the installed package, not a shadowing old checkout

```zsh
cd "$HOME"
env -u PYTHONPATH -u PYTHONHOME "$HOME/zotify/.venv/bin/zotify" --version
env -u PYTHONPATH -u PYTHONHOME "$HOME/zotify/.venv/bin/python" -c \
  'import sys, zotify.config; from importlib.metadata import version; print(sys.executable); print(zotify.config.__file__); print(version("zotify"))'
```

Expect version `0.21.0` and a concrete `zotify.config` path in the **new `.venv`**.
A namespace package can have no useful `zotify.__file__`. No activation is needed;
explicit executable paths prevent accidentally using the old command. To activate
for interactive work: `source "$HOME/zotify/.venv/bin/activate"`, then `deactivate`
when finished. Activation alone does not clear global Python path overrides.

## 4. Aliases in `~/.zshrc`

Inspect `type -a zotify zotify_playlist` and save a backup of `~/.zshrc` before
editing. Add this manually **after acceptance**, or use a temporary name first:

```zsh
alias zotify='env -u PYTHONPATH -u PYTHONHOME "$HOME/zotify/.venv/bin/zotify"'
```

Reload with `source ~/.zshrc`; check `type -a zotify` and `zotify --version`.
Resolve any existing same-name functions/aliases deliberately. Existing playlist
wrappers can embed old executable/config paths; they are not automatically updated.
Never put credentials in an alias or use a password/token command-line argument.

The manager requires its **own** environment:

```zsh
git clone --branch release/macos-compat-setup https://github.com/The-Rinzler/Zotify-MacOS-Music-Manager.git "$HOME/Zotify-MacOS-Music-Manager"
cd "$HOME/Zotify-MacOS-Music-Manager"
# Check out its review PR branch if setup is not on main yet.
PYTHON="$(brew --prefix python@3.11)/bin/python3.11" bash scripts/setup_macos.sh --test
```

Its [README](https://github.com/The-Rinzler/Zotify-MacOS-Music-Manager#readme)
contains separate playlist/consolidation aliases, the developer Client ID/Secret
setup, and destructive-action warnings. Do not combine the two dependency sets
in a production venv just to run optional integration tests.

## 5. Authenticate, smoke-test, then cut over

Use [Authentication](docs/AUTHENTICATION.md) and the README's explicit isolated
paths for **each** invocation. Keep both credential files and test music outside
the checkout. Check one small playlist, then another with an overlapping track.
Confirm MP3 codec/bitrate, five-column `.song_ids`, working M3U8s and unchanged
playlist originals before running manager operations on a copy of the test tree.

No native macOS/live-auth success is implied by Linux offline tests. Copying a
credential file or seeing a browser success page is not acceptance. Only switch
production paths/aliases after the end-to-end checks succeed.

## Updates and rollback

Review a new commit/PR before updating your checkout. After a deliberate Git
update, rerun:

```zsh
cd "$HOME/zotify"
PYTHON="$(brew --prefix python@3.11)/bin/python3.11" bash scripts/setup_macos.sh --update --test
```

`--update` only recognizes a venv created by this script in this checkout. It
reinstalls the checked-out code; it does not run `git pull`, migrate config, or
change credentials. Stop if pip reports an error; do not proceed on a partial
installation. A fresh checkout/venv is safer when testing a major dependency
change. Roll back by restoring the previous alias/executable and config backup,
not by deleting working credentials or music. To remove test artifacts, remove
only the explicitly created test directory and new test venv once no longer used.
