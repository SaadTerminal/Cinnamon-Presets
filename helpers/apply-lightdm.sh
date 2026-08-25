#!/usr/bin/env bash
# Applies a saved LightDM (slick-greeter) config, and — if the preset
# bundled them — its background image and any custom greeter theme/
# icon-theme/cursor-theme. Run via pkexec.
# Only ever touches /etc/lightdm/slick-greeter.conf,
# /usr/share/backgrounds/cinnamon-presets/, /usr/share/themes/, and
# /usr/share/icons/ — nothing else.
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

mkdir -p /etc/lightdm

if [[ -f "$DEST" ]]; then
    cp -a "$DEST" "$DEST.cinnamon-presets-backup"
fi

cp "$SRC" "$DEST"
chmod 644 "$DEST"

# $1 = bundle dir (source), $2 = install root (e.g. /usr/share/themes),
# $3 = theme/icon-set name. The ${var:?} guards make an accidentally
# empty root or name fail loudly instead of `rm -rf` silently expanding
# to something far too broad — this runs as root via pkexec.
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

if [[ -n "$BG_SRC" && -f "$BG_SRC" && -n "$PRESET_NAME" ]]; then
    mkdir -p "$BG_DEST_DIR"
    EXT="${BG_SRC##*.}"
    BG_DEST="$BG_DEST_DIR/$PRESET_NAME.$EXT"
    cp "$BG_SRC" "$BG_DEST"
    chmod 644 "$BG_DEST"

    # Point the just-installed config at our own managed copy, rather
    # than trusting the original path it was saved from to still exist —
    # that's the whole point of bundling it in the first place.
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
