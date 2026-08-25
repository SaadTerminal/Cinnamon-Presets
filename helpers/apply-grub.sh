#!/usr/bin/env bash
# Applies a saved /etc/default/grub and (optionally) a bundled GRUB theme,
# then regenerates the boot menu. Run via pkexec.
# Only ever touches /etc/default/grub, /boot/grub/themes/<name>, and runs
# update-grub — nothing else.
set -euo pipefail

SRC="${1:-}"
THEME_BUNDLE="${2:-}"
THEME_NAME="${3:-}"
DEST="/etc/default/grub"

if [[ -z "$SRC" || ! -f "$SRC" ]]; then
    echo "Source GRUB config not found: $SRC" >&2
    exit 1
fi

if [[ -f "$DEST" ]]; then
    cp -a "$DEST" "$DEST.cinnamon-presets-backup"
fi

cp "$SRC" "$DEST"

if [[ -n "$THEME_BUNDLE" && -n "$THEME_NAME" && -d "$THEME_BUNDLE" ]]; then
    DEST_THEME_DIR="/boot/grub/themes/$THEME_NAME"
    mkdir -p "$DEST_THEME_DIR"
    cp -a "$THEME_BUNDLE"/. "$DEST_THEME_DIR"/
fi

update-grub

echo "GRUB config applied and boot menu regenerated."
if [[ -f "$DEST.cinnamon-presets-backup" ]]; then
    echo "Previous config backed up to $DEST.cinnamon-presets-backup"
fi
