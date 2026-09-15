#!/usr/bin/env bash
#
# Restores /etc/default/grub from the backup apply-grub.sh already
# creates right before every overwrite, then regenerates the boot menu.
# I call this via pkexec, always as root.
#
# This undoes whatever THIS app's own most recent GRUB apply did -- it's
# not tied to any particular preset, it just reverses the last change
# this app itself made. There's only ever one rolling backup on disk
# (apply-grub.sh overwrites it every time it runs), so "restore" always
# means "undo the single most recent apply", not "pick from a history".
#
# Scope, same narrow-touch convention as every other helper here: this
# only ever writes to /etc/default/grub and runs update-grub. Nothing
# else is touched, and authorizing this never grants access to
# apply-lightdm.sh / apply-plymouth.sh / apply-grub.sh -- each pkexec
# call here is its own separate authorization.

set -euo pipefail

DEST="/etc/default/grub"
BACKUP="$DEST.cinnamon-presets-backup"

# If there's no backup, there's genuinely nothing for this app to have
# changed yet -- rather than silently doing nothing, I say so plainly
# and fail.
if [[ ! -f "$BACKUP" ]]; then
    echo "No backup found at $BACKUP -- nothing to restore." >&2
    exit 1
fi

cp -a "$BACKUP" "$DEST"
# Same reason apply-grub.sh calls this: copying the file back in isn't
# enough on its own to make it the live, bootable config -- update-grub
# is what actually regenerates the real boot menu from it.
update-grub

echo "GRUB config restored from backup and boot menu regenerated."
