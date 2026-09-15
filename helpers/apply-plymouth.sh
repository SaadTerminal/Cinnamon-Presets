#!/usr/bin/env bash
#
# Applies a saved Plymouth boot-splash theme. I call this via pkexec from
# the main app, always as root.
#
# Scope: this only ever writes to /usr/share/plymouth/themes/<theme> and
# rebuilds the initramfs. Nothing else on the system is touched.
#
# Arguments:
#   $1  THEME        the Plymouth theme name to select (required)
#   $2  BUNDLE_DIR    path to that theme's bundled files, or empty
#
# If the theme is already installed on this system, BUNDLE_DIR is ignored
# entirely -- I only ever install from the bundle when the theme ISN'T
# already present, never overwrite an existing system installation of it.

set -euo pipefail

THEME="${1:-}"
BUNDLE_DIR="${2:-}"
DEST_DIR="/usr/share/plymouth/themes/$THEME"

if [[ -z "$THEME" ]]; then
    echo "No theme name given." >&2
    exit 1
fi

# Only install from the bundle if this exact theme folder doesn't already
# exist -- if Plymouth (or a package) already has it, I leave that
# existing installation alone rather than clobbering it with the bundled
# copy.
if [[ -n "$BUNDLE_DIR" && -d "$BUNDLE_DIR" && ! -d "$DEST_DIR" ]]; then
    mkdir -p "$DEST_DIR"
    cp -a "$BUNDLE_DIR"/. "$DEST_DIR"/
fi

# By this point the theme needs to actually exist on disk -- either it
# was already installed, or the bundle step above just installed it. If
# neither happened, there's genuinely nothing to select.
if [[ ! -d "$DEST_DIR" ]]; then
    echo "Plymouth theme '$THEME' isn't installed on this system and no bundled copy was found in the preset." >&2
    exit 1
fi

# Select the theme. update-alternatives is the actual mechanism
# Debian/Ubuntu/Mint use to register the active Plymouth theme -- it's
# what `update-alternatives --config default.plymouth` edits when run
# interactively. I drive it directly here rather than only going through
# plymouth-set-default-theme, because on some systems that command
# doesn't reliably report or select the theme the same way
# update-alternatives does.
PLYMOUTH_CONF="$(find "$DEST_DIR" -maxdepth 1 -name '*.plymouth' | head -n1)"

if command -v update-alternatives >/dev/null 2>&1 && [[ -n "$PLYMOUTH_CONF" ]]; then
    # --install registers the alternative if it isn't already known;
    # `|| true` because it's entirely normal for this exact alternative
    # to already be registered from a previous run, and that's not a
    # failure worth stopping over. --set is the actual selection step.
    update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth "$PLYMOUTH_CONF" 100 >/dev/null 2>&1 || true
    update-alternatives --set default.plymouth "$PLYMOUTH_CONF"
elif command -v plymouth-set-default-theme >/dev/null 2>&1; then
    plymouth-set-default-theme "$THEME"
else
    echo "Neither update-alternatives nor plymouth-set-default-theme is available." >&2
    exit 1
fi

# Rebuild the initramfs myself, explicitly, regardless of which of the
# two methods above actually set the theme -- Plymouth's boot-time splash
# is baked into the initramfs image, so selecting a theme alone does
# nothing to what's actually shown at boot until this runs.
update-initramfs -u

echo "Plymouth theme set to '$THEME' and initramfs rebuilt (update-initramfs -u)."
