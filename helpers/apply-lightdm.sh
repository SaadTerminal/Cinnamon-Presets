#!/usr/bin/env bash
#
# Applies a saved LightDM (slick-greeter) config, and -- if the preset
# bundled them -- its login-screen background image and any custom
# greeter theme / icon-theme / cursor-theme. I call this via pkexec from
# the main app, always as root.
#
# Scope, same convention as every other helper here: this only ever
# touches /etc/lightdm/slick-greeter.conf, /usr/share/backgrounds/
# cinnamon-presets/, /usr/share/themes/, and /usr/share/icons/. Nothing
# else on the system is written.
#
# Arguments (all positional; only $1 is required):
#   $1  SRC           path to the saved slick-greeter.conf (required)
#   $2  BG_SRC         path to the bundled background image, or empty
#   $3  PRESET_NAME     preset name, used to name the installed background
#   $4  GTK_NAME         GTK theme name to install for the greeter, or empty
#   $5  GTK_BUNDLE       path to that theme's bundled files, or empty
#   $6  ICON_NAME        icon theme name, or empty
#   $7  ICON_BUNDLE      path to that icon theme's bundled files, or empty
#   $8  CURSOR_NAME       cursor theme name, or empty
#   $9  CURSOR_BUNDLE     path to that cursor theme's bundled files, or empty
#
# Every one of the theme/icon/cursor pairs is independently optional --
# the main app only fills in a NAME/BUNDLE pair when that particular
# thing was actually bundled with the preset. Missing a pair just means
# "leave that part of the greeter's look alone", not an error.

set -euo pipefail

SRC="${1:-}"
BG_SRC="${2:-}"
PRESET_NAME="${3:-}"
GTK_NAME="${4:-}"
GTK_BUNDLE="${5:-}"
ICON_NAME="${6:-}"
ICON_BUNDLE="${7:-}"
CURSOR_NAME="${8:-}"
CURSOR_BUNDLE="${9:-}"
DEST="/etc/lightdm/slick-greeter.conf"
BG_DEST_DIR="/usr/share/backgrounds/cinnamon-presets"

if [[ -z "$SRC" || ! -f "$SRC" ]]; then
    echo "Source LightDM config not found: $SRC" >&2
    exit 1
fi

# /etc/lightdm might not exist at all on a from-scratch system --
# LightDM itself would normally create it, but I don't want to depend on
# that happening first.
mkdir -p /etc/lightdm

# Same rolling-backup convention as apply-grub.sh: one backup, overwritten
# every time this runs, read back by restore-lightdm.sh. If there's
# nothing live yet, there's nothing to back up.
if [[ -f "$DEST" ]]; then
    cp -a "$DEST" "$DEST.cinnamon-presets-backup"
fi

cp "$SRC" "$DEST"
# slick-greeter reads this as its own system user, not as the person who
# owns the file -- world-readable is what actually makes the config
# usable at the login screen.
chmod 644 "$DEST"

# Installs one theme/icon/cursor asset under a system-wide root
# (/usr/share/themes or /usr/share/icons), replacing any existing copy
# under that exact name.
#   $1 = bundle dir (source, inside the preset)
#   $2 = install root (e.g. /usr/share/themes)
#   $3 = theme/icon-set name (the folder name it gets installed as)
#
# The ${var:?} guards on root/name are deliberate: if either one somehow
# ended up empty, `rm -rf "$root/$name"` would silently expand to
# `rm -rf /usr/share/themes/` or worse. This runs as root via pkexec, so
# I want that kind of mistake to fail loudly and immediately instead of
# quietly deleting far more than intended.
install_theme_asset() {
    local bundle="$1" root="$2" name="$3"
    if [[ -n "$bundle" && -d "$bundle" && -n "$name" ]]; then
        mkdir -p "$root"
        rm -rf "${root:?}/${name:?}"
        cp -a "$bundle" "$root/$name"
    fi
}

install_theme_asset "$GTK_BUNDLE" "/usr/share/themes" "$GTK_NAME"
install_theme_asset "$ICON_BUNDLE" "/usr/share/icons" "$ICON_NAME"
install_theme_asset "$CURSOR_BUNDLE" "/usr/share/icons" "$CURSOR_NAME"

# Install the login-screen background, if the preset bundled one, and
# point the config at it.
if [[ -n "$BG_SRC" && -f "$BG_SRC" && -n "$PRESET_NAME" ]]; then
    mkdir -p "$BG_DEST_DIR"
    EXT="${BG_SRC##*.}"
    BG_DEST="$BG_DEST_DIR/$PRESET_NAME.$EXT"
    cp "$BG_SRC" "$BG_DEST"
    chmod 644 "$BG_DEST"

    # I point the just-installed config at my own managed copy under
    # $BG_DEST_DIR, rather than trusting the path the image was
    # originally saved from to still exist -- that original path could
    # be a user's home directory file that's since moved or been
    # deleted, and bundling the image into the preset in the first place
    # only helps if I actually use the bundled copy.
    if grep -q '^background=' "$DEST"; then
        sed -i "s|^background=.*|background=$BG_DEST|" "$DEST"
    else
        printf '\nbackground=%s\n' "$BG_DEST" >> "$DEST"
    fi
    echo "LightDM greeter config and background image applied."
else
    echo "LightDM greeter config applied."
fi

if [[ -f "$DEST.cinnamon-presets-backup" ]]; then
    echo "Previous config backed up to $DEST.cinnamon-presets-backup"
fi
