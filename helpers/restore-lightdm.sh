#!/usr/bin/env bash
#
# Restores /etc/lightdm/slick-greeter.conf from the backup
# apply-lightdm.sh already creates right before every overwrite
# (cp -a "$DEST" "$DEST.cinnamon-presets-backup"). I call this via
# pkexec, always as root.
#
# Same model as restore-grub.sh: this undoes whatever THIS app's own
# most recent LightDM apply did, regardless of which preset that was --
# not a per-preset undo, just a reversal of the single most recent
# change this app made. Only one rolling backup exists on disk at a
# time, since apply-lightdm.sh overwrites it on every run.
#
# Scope: this only ever writes to /etc/lightdm/slick-greeter.conf.
# Nothing else is touched -- notably, this does NOT undo any bundled
# theme/icon/cursor/background files apply-lightdm.sh may have installed
# under /usr/share/; only the config file itself is reverted.

set -euo pipefail

DEST="/etc/lightdm/slick-greeter.conf"
BACKUP="$DEST.cinnamon-presets-backup"

if [[ ! -f "$BACKUP" ]]; then
    echo "No LightDM backup found at $BACKUP -- nothing to restore." >&2
    exit 1
fi

cp -a "$BACKUP" "$DEST"
# Same reasoning as apply-lightdm.sh: slick-greeter reads this file as
# its own system user, so it needs to stay world-readable for the login
# screen to actually pick it up.
chmod 644 "$DEST"

echo "LightDM greeter config restored from backup."
