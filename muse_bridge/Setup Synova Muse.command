#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

echo "Synova Muse 2 setup"
echo "This installs the local BrainFlow headset library in the Synova folder."
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it, then run this setup again."
  read -r "?Press Return to close."
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Setup complete. Double-click Start Synova Muse.command whenever you use the headset."
read -r "?Press Return to close."
