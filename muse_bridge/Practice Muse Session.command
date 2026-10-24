#!/bin/zsh
set -uo pipefail

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "Run Setup Synova Muse.command first."
  read -r "?Press Return to close."
  exit 1
fi

echo "Short Muse practice: six REST and six imagined right-hand opening trials."
echo "Complete Check Muse Connection.command first and close all other Muse connections."
echo "The session is saved locally but excluded from model training and evaluation."
read -r "PARTICIPANT?Participant code (e.g. P01): "

.venv/bin/python -u record_open_rest.py --participant "$PARTICIPANT" --practice
RESULT=$?
echo
echo "Run Check Synova Data.command to review usable practice trials."
read -r "?Press Return to close."
exit "$RESULT"
