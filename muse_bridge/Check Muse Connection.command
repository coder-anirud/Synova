#!/bin/zsh
set -uo pipefail
SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"
if [[ ! -x .venv/bin/python ]]; then
  echo "Run Setup Synova Muse.command first."
  read -r "?Press Return to close."
  exit 1
fi
echo "Turn on Muse 2, fit it, and sit still. Close Muse/Mind Monitor and other bridge windows."
echo "Allow Bluetooth access to Terminal if macOS asks."
echo "This check reads EEG but saves only a diagnostic summary."
.venv/bin/python -u check_headset.py --output data/diagnostics/latest_headset_check.json
RESULT=$?
echo
if [[ "$RESULT" -eq 0 ]]; then
  echo "Basic signal checks passed. Next: Record Synova Training.command."
else
  echo "Check System Settings > Privacy & Security > Bluetooth for Terminal access."
  echo "If samples arrived but quality failed, adjust headset contact and try again."
fi
read -r "?Press Return to close."
exit "$RESULT"
