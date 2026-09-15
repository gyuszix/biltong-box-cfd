#!/usr/bin/env bash
# Wrapper around make_gif.py that finds the repo's shared .venv
# automatically, so you never have to remember the venv path or activate
# anything - just run this script directly (./make_gif.sh) from anywhere.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/../../.venv/bin/python" "$ROOT/make_gif.py" "$@"
