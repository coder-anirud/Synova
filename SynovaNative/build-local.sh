#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
APP_DIR="$SCRIPT_DIR/build/Synova.app"
CONTENTS_DIR="$APP_DIR/Contents"

cd "$PROJECT_DIR"
npm run native:assets

mkdir -p "$CONTENTS_DIR/MacOS" "$CONTENTS_DIR/Resources/Web"
/bin/cp -R "$SCRIPT_DIR/Sources/SynovaNative/Resources/Web/." "$CONTENTS_DIR/Resources/Web/"
/bin/cp "$SCRIPT_DIR/Launcher/Info.plist" "$CONTENTS_DIR/Info.plist"

/usr/bin/clang -fobjc-arc \
    -framework Cocoa \
    -framework WebKit \
    "$SCRIPT_DIR/Launcher/main.m" \
    -o "$CONTENTS_DIR/MacOS/Synova"

echo "$APP_DIR"
