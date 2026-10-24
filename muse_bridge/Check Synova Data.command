#!/bin/zsh
set -uo pipefail

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "Run Setup Synova Muse.command first."
  read -r "?Press Return to close."
  exit 1
fi

echo "Synova EEG data check"
read -r "PARTICIPANT?Participant code: "
echo
.venv/bin/python train_open_rest.py --participant "$PARTICIPANT" --inspect
RESULT=$?
echo
echo "Usable trials exclude obvious flatline and high-amplitude signal artifacts."
read -r "?Press Return to close."
exit "$RESULT"
