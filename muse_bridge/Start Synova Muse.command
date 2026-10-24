#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "Run Setup Synova Muse.command first."
  read -r "?Press Return to close."
  exit 1
fi

KEY_FILE="$SCRIPT_DIR/.access-key"
if [[ ! -f "$KEY_FILE" ]]; then
  .venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(24))' > "$KEY_FILE"
  chmod 600 "$KEY_FILE"
fi

ACCESS_KEY="$(<"$KEY_FILE")"
MAC_ADDRESS="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"

echo "Synova Muse 2 companion"
echo
if [[ -n "$MAC_ADDRESS" ]]; then
  echo "Mac address for the iPhone app: ${MAC_ADDRESS}:8765"
else
  echo "Mac address: check System Settings → Wi-Fi → Details → IP Address"
fi
echo "Access key for the iPhone app: $ACCESS_KEY"
echo
echo "Turn on Muse 2 and keep this window open."
echo "This companion displays EEG in the app. Use record.py separately to collect training trials."
echo

exec .venv/bin/python server.py --host 0.0.0.0 --access-key "$ACCESS_KEY"
