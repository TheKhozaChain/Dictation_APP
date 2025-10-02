#!/usr/bin/env bash
set -euo pipefail

PLIST_NAME="com.local.dictate.menubar"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

launchctl unload "$PLIST_PATH" 2>/dev/null || true
rm -f "$PLIST_PATH"
echo "Uninstalled: $PLIST_PATH"




