#!/usr/bin/env bash
# Restores /etc/lightdm/slick-greeter.conf from the backup apply-lightdm.sh
# already creates before every overwrite (cp -a "$DEST" "$DEST.cinnamon-presets-backup").
# Undoes whatever this app's own most recent LightDM apply did, regardless
# of which preset that was -- run via pkexec, same narrow-scope pattern as
# restore-grub.sh.
set -euo pipefail

DEST="/etc/lightdm/slick-greeter.conf"
BACKUP="$DEST.cinnamon-presets-backup"

if [[ ! -f "$BACKUP" ]]; then
    echo "No LightDM backup found at $BACKUP — nothing to restore." >&2
    exit 1
fi

cp -a "$BACKUP" "$DEST"
chmod 644 "$DEST"

echo "LightDM greeter config restored from backup."
