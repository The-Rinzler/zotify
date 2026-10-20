# macOS installation and updates

This guide installs this fork from source into its own project-local `.venv`. It leaves any existing Zotify environment, account files, shell aliases, and music library in place.

## 1. Install prerequisites

Install [Homebrew](https://brew.sh/) if needed, then run:

```zsh
brew install python@3.11 git ffmpeg
command -v ffmpeg ffprobe
ffmpeg -version
ffprobe -version
ffmpeg -hide_banner -encoders 2>/dev/null | /usr/bin/grep libmp3lame
```

Python 3.11 is recommended (the project requires Python 3.10+). The MP3 workflow needs an MP3 encoder; the stock Homebrew FFmpeg is the recommended starting point. Do not use `sudo pip`, system Python, or another project's venv.

## 2. Clone this fork and install it

```zsh
git clone --branch compat/macos-ipod https://github.com/The-Rinzler/zotify.git "$HOME/zotify"
cd "$HOME/zotify"
PYTHON="$(brew --prefix python@3.11)/bin/python3.11" bash scripts/setup_macos.sh
```

If `~/zotify` exists, choose a different empty destination and adjust the paths below. `bash scripts/setup_macos.sh --help` lists the supported options.

The script resolves paths relative to its own checkout, clears `PYTHONPATH` and `PYTHONHOME`, refuses to replace an existing `.venv`, installs this checkout, verifies dependency consistency, and checks CLI startup. It does not log in, edit shell files, install Homebrew, or alter user data. PyPI dependencies are not fully locked, so later installs can select newer versions allowed by the project constraints.

To verify which installation will run:

```zsh
"$HOME/zotify/.venv/bin/zotify" --version
"$HOME/zotify/.venv/bin/python" -c \
  'import sys, zotify.config; from importlib.metadata import version; print(sys.executable); print(zotify.config.__file__); print(version("zotify"))'
```

Expect version `0.21.0` and a `zotify.config` path inside the new `.venv`. Using the explicit executable avoids an older checkout or environment shadowing this install. You do not need to activate the venv; for interactive work, use `source "$HOME/zotify/.venv/bin/activate"` and `deactivate` when finished.

## 3. Configure first use

The default `config.json` is created on first launch under `~/Library/Application Support/Zotify/`; credentials are saved there after successful authorization. The default destinations are `~/Music/Zotify Music` for music and `~/Music/Zotify Podcasts` for podcasts. Review the paths and output settings in that file before starting a large download. You can also pass `--root-path` and `--root-podcast-path` for a specific invocation.

See [Authentication](docs/AUTHENTICATION.md) for the first browser sign-in and optional Developer API setup. Start with one intended track or other small item to complete first-run sign-in and confirm the chosen output directory; then run the playlist, album, or other job you want.

## 4. Add an alias to `~/.zshrc`

Inspect `type -a zotify zotify_playlist` and back up `~/.zshrc`. Add a unique alias manually so existing commands and playlist wrappers remain usable:

```zsh
alias zotify_mac='env -u PYTHONPATH -u PYTHONHOME "$HOME/zotify/.venv/bin/zotify"'
```

Reload and verify:

```zsh
source ~/.zshrc
type -a zotify_mac
zotify_mac --version
```

If you intend to replace a same-name alias or function, review its current definition and keep a rollback copy before changing it. Never place credentials in shell aliases or command-line arguments.

The companion manager uses a separate repository and separate environment. Follow its [installation guide](https://github.com/The-Rinzler/Zotify-MacOS-Music-Manager/blob/main/INSTALLATION.md); do not combine the two dependency sets in one venv.

## Updates and rollback

Review the change and update the checkout deliberately. To update a venv previously created by this script in this checkout:

```zsh
cd "$HOME/zotify"
git fetch origin
git pull --ff-only origin compat/macos-ipod
PYTHON="$(brew --prefix python@3.11)/bin/python3.11" bash scripts/setup_macos.sh --update
```

`--update` only accepts a venv with this checkout's ownership marker. It reinstalls the checked-out source; it does not run Git commands, migrate configuration, or change credentials. If the environment is not recognized, stop and use a new empty clone rather than pointing setup at an existing production venv.

For rollback, restore the previous executable or shell alias and configuration backup. Keep existing account files and music directories unless you deliberately manage them yourself; installing or updating Zotify does not require deleting either.