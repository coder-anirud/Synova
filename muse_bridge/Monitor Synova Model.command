#!/bin/zsh
set -uo pipefail

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "Run Setup Synova Muse.command first."
  read -r "?Press Return to close."
  exit 1
fi

echo "Display-only EEG model monitor. This does not control or connect to the glove."
echo "Stop Start Synova Muse.command and other Muse connections first."
echo "Only run this after Train Synova Model.command saves a checkpoint."
read -r "PARTICIPANT?Participant code: "
read -r "CONDITION?Condition [unlabeled/rest/imagined_open]: "
CONDITION="${CONDITION:-unlabeled}"
read -r "DURATION?Seconds [60; use 300 for a five-minute rest check]: "
DURATION="${DURATION:-60}"

.venv/bin/python -u monitor_open_rest.py --participant "$PARTICIPANT" --condition "$CONDITION" --duration "$DURATION"
RESULT=$?
echo
echo "Review the summary in data/monitor. Candidate events are research observations, not physical movements."
read -r "?Press Return to close."
exit "$RESULT"
