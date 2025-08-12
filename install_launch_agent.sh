#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/Users/siphokhoza/willow_competitor"
PY="$APP_DIR/.venv/bin/python"
SCRIPT="$APP_DIR/dictate.py"
PLIST_NAME="com.local.dictate"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
      <string>$PY</string>
      <string>-u</string>
      <string>$SCRIPT</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$APP_DIR/dictate.log</string>
    <key>StandardErrorPath</key>
    <string>$APP_DIR/dictate.log</string>
    <key>EnvironmentVariables</key>
    <dict>
      <key>WILLOW_SOUND</key><string>1</string>
    </dict>
    <key>ProcessType</key>
    <string>Interactive</string>
  </dict>
  </plist>
PLIST

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
launchctl start "$PLIST_NAME"
echo "Installed and launched: $PLIST_PATH"


