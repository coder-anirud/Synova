#!/bin/zsh
set -uo pipefail

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "Run Setup Synova Muse.command first."
  read -r "?Press Return to close."
  exit 1
fi

echo "Synova independent model review"
echo "This scores the reserved final session once. Finalize your model before running."
read -r "PARTICIPANT?Participant code: "
echo
.venv/bin/python train_open_rest.py --participant "$PARTICIPANT" --final-test "models/${PARTICIPANT}_open_rest.joblib"
RESULT=$?
echo
echo "This evaluation is offline. Nothing is sent to the glove."
read -r "?Press Return to close."
exit "$RESULT"
