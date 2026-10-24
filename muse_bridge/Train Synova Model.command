#!/bin/zsh
set -uo pipefail

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "Run Setup Synova Muse.command first."
  read -r "?Press Return to close."
  exit 1
fi

echo "Synova offline research model"
echo "Six complete two-class sessions required. The last two are reserved for validation and final testing."
read -r "PARTICIPANT?Participant code: "
mkdir -p models
echo

.venv/bin/python train_open_rest.py --participant "$PARTICIPANT" --output "models/${PARTICIPANT}_open_rest.joblib"
RESULT=$?

echo
echo "This result is an offline feasibility test. It does not enable glove control."
read -r "?Press Return to close."
exit "$RESULT"
