#!/usr/bin/env bash
# Applies a saved Plymouth boot-splash theme. Run via pkexec.
# Only ever touches /usr/share/plymouth/themes/<theme> and rebuilds the
# initramfs — nothing else.
set -euo pipefail

THEME="${1:-}"
BUNDLE_DIR="${2:-}"
DEST_DIR="/usr/share/plymouth/themes/$THEME"

if [[ -z "$THEME" ]]; then
    echo "No theme name given." >&2
    exit 1
fi

if [[ -n "$BUNDLE_DIR" && -d "$BUNDLE_DIR" && ! -d "$DEST_DIR" ]]; then
    mkdir -p "$DEST_DIR"
    cp -a "$BUNDLE_DIR"/. "$DEST_DIR"/
fi

if [[ ! -d "$DEST_DIR" ]]; then
    echo "Plymouth theme '$THEME' isn't installed on this system and no bundled copy was found in the preset." >&2
    exit 1
fi

# Select the theme. update-alternatives is the mechanism Debian/Ubuntu/
# Mint actually register the theme choice through (this is what
# `update-alternatives --config default.plymouth` edits interactively) --
# so we drive it directly rather than only going through
# plymouth-set-default-theme, which on some systems doesn't reliably
# report/select the theme the same way.
PLYMOUTH_CONF="$(find "$DEST_DIR" -maxdepth 1 -name '*.plymouth' | head -n1)"

if command -v update-alternatives >/dev/null 2>&1 && [[ -n "$PLYMOUTH_CONF" ]]; then
    update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth "$PLYMOUTH_CONF" 100 >/dev/null 2>&1 || true
    update-alternatives --set default.plymouth "$PLYMOUTH_CONF"
elif command -v plymouth-set-default-theme >/dev/null 2>&1; then
    plymouth-set-default-theme "$THEME"
else
    echo "Neither update-alternatives nor plymouth-set-default-theme is available." >&2
    exit 1
fi

# Rebuild the initramfs ourselves explicitly, regardless of which method
# above set the theme, so it always happens and always gets reported.
update-initramfs -u

echo "Plymouth theme set to '$THEME' and initramfs rebuilt (update-initramfs -u)."
