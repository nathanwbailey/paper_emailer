#!/usr/bin/env bash
set -euo pipefail

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip uv

if [ -f pyproject.toml ] && { [ -d src ] || [ -d paper_emailer ]; }; then
  uv sync --extra dev
fi
