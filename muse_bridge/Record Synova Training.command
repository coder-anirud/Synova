#!/bin/zsh
set -uo pipefail

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "Run Setup Synova Muse.command first."
  read -r "?Press Return to close."
  exit 1
fi

echo "NeuroGrip / Synova: rest versus imagined right-hand opening"
echo "Close Start Synova Muse.command first; only one program can use the headset."
echo "Use a short pseudonym, not your real name."
read -r "PARTICIPANT?Participant code: "
read -r "TRIALS?Trials per class [30]: "
TRIALS="${TRIALS:-30}"
echo

.venv/bin/python -u record_open_rest.py --participant "$PARTICIPANT" --per-class "$TRIALS"
RESULT=$?

echo
echo "Run Check Synova Data.command to inspect saved trials. Plan target: six sessions across at least seven days."
read -r "?Press Return to close."
exit "$RESULT"
