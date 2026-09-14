#!/usr/bin/env bash
# Wrapper around compare_variants.py that finds the repo's shared .venv
# automatically, so you never have to remember the venv path or activate
# anything - just run this script directly (./compare.sh) from anywhere.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/../../.venv/bin/python" "$ROOT/compare_variants.py" "$@"
