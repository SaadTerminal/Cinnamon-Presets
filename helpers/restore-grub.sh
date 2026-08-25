#!/usr/bin/env bash
# Restores /etc/default/grub from the backup apply-grub.sh already
# creates before every overwrite, then regenerates the boot menu.
# Run via pkexec. Only ever touches /etc/default/grub and runs
# update-grub — nothing else, same narrow-scope convention as every
# other helper here (authorizing this never grants access to
# apply-lightdm.sh / apply-plymouth.sh / apply-grub.sh).
set -euo pipefail

DEST="/etc/default/grub"
BACKUP="$DEST.cinnamon-presets-backup"

if [[ ! -f "$BACKUP" ]]; then
    echo "No backup found at $BACKUP -- nothing to restore." >&2
    exit 1
fi

cp -a "$BACKUP" "$DEST"
update-grub

echo "GRUB config restored from backup and boot menu regenerated."
