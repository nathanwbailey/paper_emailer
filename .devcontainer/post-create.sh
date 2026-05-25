#!/usr/bin/env bash
set -euo pipefail

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip

if [ -f requirements.txt ]; then
  pip install -r requirements.txt
elif [ -f pyproject.toml ] && { [ -d src ] || [ -d paper_emailer ]; }; then
  pip install -e ".[dev]"
fi
