#!/usr/bin/env bash
#
# Applies a saved /etc/default/grub config and, if the preset bundled one,
# a custom GRUB theme, then regenerates the boot menu. I call this via
# pkexec from the main app -- it always runs as root, and it's the one
# helper here with the worst realistic failure mode (a broken boot menu),
# so I keep its blast radius as small and obvious as I can:
#
#   - Only ever writes to /etc/default/grub and /boot/grub/themes/<name>
#   - Only ever runs update-grub
#   - Nothing else on the system is touched
#
# Arguments (all positional, all optional except $1):
#   $1  SRC          path to the saved grub config to install (required)
#   $2  THEME_BUNDLE  path to a bundled GRUB theme directory (optional)
#   $3  THEME_NAME    name to install that theme under (optional)
#
# The main app is responsible for deciding whether a theme should be
# installed at all -- if it doesn't want one applied, it just leaves $2/$3
# empty and this script quietly skips that whole step.

set -euo pipefail

SRC="${1:-}"
THEME_BUNDLE="${2:-}"
THEME_NAME="${3:-}"
DEST="/etc/default/grub"

# Fail loudly and early if there's nothing to apply -- better than
# silently no-op'ing and telling the person it worked.
if [[ -z "$SRC" || ! -f "$SRC" ]]; then
    echo "Source GRUB config not found: $SRC" >&2
    exit 1
fi

# Back up whatever's live right now, before I overwrite it. This is the
# ONLY backup this app ever keeps for GRUB (one rolling backup, not a
# history) -- restore-grub.sh reads this exact file back. If nothing's
# there yet (a from-scratch install with no /etc/default/grub at all,
# unlikely but not impossible), there's nothing to back up and that's fine.
if [[ -f "$DEST" ]]; then
    cp -a "$DEST" "$DEST.cinnamon-presets-backup"
fi

cp "$SRC" "$DEST"

# Install the bundled GRUB theme, if the preset has one. I only do this
# when all three pieces are actually present -- a bundle dir, a name to
# install it under, and that dir actually existing on disk. Any missing
# piece just means "no theme for this preset", not an error.
if [[ -n "$THEME_BUNDLE" && -n "$THEME_NAME" && -d "$THEME_BUNDLE" ]]; then
    DEST_THEME_DIR="/boot/grub/themes/$THEME_NAME"
    mkdir -p "$DEST_THEME_DIR"
    cp -a "$THEME_BUNDLE"/. "$DEST_THEME_DIR"/
fi

# This is what actually turns the new /etc/default/grub into a real,
# bootable GRUB config -- without this, the file I just copied in is
# inert until the next unrelated update-grub run touches it.
update-grub

echo "GRUB config applied and boot menu regenerated."
if [[ -f "$DEST.cinnamon-presets-backup" ]]; then
    echo "Previous config backed up to $DEST.cinnamon-presets-backup"
fi
