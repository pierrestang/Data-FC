#!/bin/sh
# Installe (ou réinstalle) la tâche nocturne launchd. Désinstaller : ./install.sh --remove
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="$HOME/Library/LaunchAgents/com.datafc.update.plist"
launchctl bootout "gui/$(id -u)" "$DEST" 2>/dev/null || true
if [ "$1" = "--remove" ]; then rm -f "$DEST"; echo "Tâche retirée."; exit 0; fi
mkdir -p "$ROOT/logs" "$HOME/Library/LaunchAgents"
sed "s#__ROOT__#$ROOT#g" "$ROOT/scraper/launchd/com.datafc.update.plist" > "$DEST"
launchctl bootstrap "gui/$(id -u)" "$DEST"
echo "Tâche installée : $DEST (tous les jours à 00:00)"
