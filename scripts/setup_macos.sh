#!/bin/bash
# Run with bash; compatible with the Bash 3.2 shipped by macOS.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
UPDATE=0
RUN_TESTS=0
for arg in "$@"; do
    case "$arg" in
        --update) UPDATE=1 ;;
        --test) RUN_TESTS=1 ;;
        -h|--help)
            printf 'Usage: bash scripts/setup_macos.sh [--update] [--test]\nCreates .venv; --update permits reuse of an environment created here.\nPYTHON=/path/to/python3.11 selects an interpreter. No shell/config edits.\n'
            exit 0 ;;
        *) printf 'ERROR: Unknown argument: %s\n' "$arg" >&2; exit 1 ;;
    esac
done
if [ "$(uname -s)" != Darwin ]; then
    printf 'ERROR: This setup script supports macOS only.\n' >&2
    exit 1
fi
# Homebrew's site-packages and a trailing PYTHONPATH colon break isolation.
unset PYTHONPATH PYTHONHOME
VENV="$ROOT/.venv"
MARKER="$VENV/.zotify-setup-root"
if [ -e "$VENV" ] || [ -L "$VENV" ]; then
    if [ "$UPDATE" -ne 1 ]; then
        printf 'ERROR: %s already exists; nothing changed. Use --update only for a venv created by this script.\n' "$VENV" >&2
        exit 1
    fi
    if [ -L "$VENV" ] || [ ! -f "$MARKER" ] || [ "$(<"$MARKER")" != "$ROOT" ] || [ ! -x "$VENV/bin/python" ]; then
        printf 'ERROR: Refusing to update an unrecognized environment: %s\n' "$VENV" >&2
        exit 1
    fi
fi
PYTHON_BIN="${PYTHON:-python3.11}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    printf 'ERROR: Python not found: %s. Install Homebrew python@3.11, or set PYTHON to its full path.\n' "$PYTHON_BIN" >&2
    exit 1
fi
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ required (3.11 recommended)"'
for tool in git ffmpeg ffprobe; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'ERROR: Missing %s. Install git and ffmpeg with Homebrew first.\n' "$tool" >&2
        exit 1
    fi
done
# Build the project's MP3 workflow, not a similarly named package on PyPI.
cd "$ROOT"
if [ ! -d "$VENV" ]; then
    "$PYTHON_BIN" -m venv "$VENV"
    printf '%s\n' "$ROOT" > "$MARKER"
fi
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install "$ROOT"
"$VENV/bin/python" -m pip check
"$VENV/bin/python" -c 'import sys, importlib.metadata as m; print("Python:", sys.executable); print("Zotify:", m.version("zotify")); print("librespot:", m.version("librespot"))'
"$VENV/bin/zotify" --help >/dev/null
if [ "$RUN_TESTS" -eq 1 ]; then
    "$VENV/bin/python" -m pip install pytest
    "$VENV/bin/python" -m pytest tests -q
fi
printf '\nReady: %s/bin/zotify\nSee README.md and docs/AUTHENTICATION.md before first login.\n' "$VENV"
