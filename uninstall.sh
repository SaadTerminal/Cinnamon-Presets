#!/usr/bin/env bash
# Uninstalls Cinnamon Presets for the current user.
#
# By default this leaves ~/.config/cinnamon-presets (your saved presets)
# completely alone, so reinstalling later picks up right where you left
# off. Pass --purge if you actually want your saved presets deleted too.

set -euo pipefail

PURGE=false
if [[ "${1:-}" == "--purge" ]]; then
    PURGE=true
fi

BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/128x128/apps"
SCALABLE_ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
# The whole shared-data directory, not just helpers/ -- install.sh also
# populates icons/categories/ under here, and a narrower `rm -rf
# "$SHARE_DIR/helpers"` would leave that orphaned behind. Keep this in
# sync with INSTALLED_SHARE_DIR in cinnamon-presets.py's own native
# uninstall_app() if either ever changes.
SHARE_DIR="$HOME/.local/share/cinnamon-presets"
CONFIG_DIR="$HOME/.config/cinnamon-presets"

echo "Removing Cinnamon Presets..."

rm -f "$BIN_DIR/cinnamon-presets"
rm -f "$APPS_DIR/cinnamon-presets.desktop"
rm -f "$ICON_DIR/cinnamon-presets.svg"
rm -f "$SCALABLE_ICON_DIR/cinnamon-presets.svg"
rm -rf "$SHARE_DIR"

if $PURGE; then
    rm -rf "$CONFIG_DIR"
    echo "Removed app files AND your saved presets ($CONFIG_DIR)."
else
    echo "Removed app files. Your saved presets are untouched at:"
    echo "  $CONFIG_DIR"
    echo "Run with --purge instead if you wanted those deleted too."
fi
