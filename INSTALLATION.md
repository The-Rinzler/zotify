# Installing Zotify

> **macOS**

- Open the Terminal app
- Install *Homebrew* (https://brew.sh) by running: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- After installing Homebrew run: `brew install python@3.11 pipx ffmpeg git`
- Setup pipx: `pipx ensurepath`
- Install Zotify: `pipx install git+https://github.com/Googolplexed0/zotify.git`
- Done! Use `zotify --help` for a basic list of commands or check the README.md file in Zotify's code repository for full documentation.

### Note on librespot

Do **not** run `pip install librespot`. The PyPI release is outdated for this workflow.
Use the patched fork instead (required by my Zotify fork):

```bash
# inside your Zotify venv
python -m pip install "librespot @ git+https://github.com/Googolplexed0/librespot-python.git@proto-ext-metadata"
