#!/usr/bin/env bash
# Installs Cinnamon Presets for the current user.
#
# This only ever copies files INTO ~/.local/bin, ~/.local/share/applications,
# ~/.local/share/icons, and ~/.local/share/cinnamon-presets/helpers -- it
# never touches ~/.config/cinnamon-presets, which is where your saved
# presets live. Reinstalling/upgrading is always safe for your presets.
#
# Nothing here requires root. The only root prompts you'll ever see come
# later, inside the app itself, when you explicitly apply LightDM/
# Plymouth/GRUB from the "System Boot Settings" dialog.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/128x128/apps"
SCALABLE_ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
HELPERS_DIR="$HOME/.local/share/cinnamon-presets/helpers"
CATEGORY_ICONS_DIR="$HOME/.local/share/cinnamon-presets/icons/categories"
UI_ICONS_DIR="$HOME/.local/share/cinnamon-presets/icons/ui"
SHARE_DIR="$HOME/.local/share/cinnamon-presets"

echo "Installing Cinnamon Presets..."

mkdir -p "$BIN_DIR" "$APPS_DIR" "$ICON_DIR" "$SCALABLE_ICON_DIR" "$HELPERS_DIR" "$CATEGORY_ICONS_DIR" "$UI_ICONS_DIR"

if [[ -d "$SCRIPT_DIR/.git" ]]; then
    # Git checkout: symlink instead of copy, so the installed app IS this
    # clone. Self-update (git pull, see perform_git_update() in the app)
    # resolves __file__ through the symlink back to this real .git dir --
    # that's what makes it work after install.sh, not just when running
    # straight out of the clone. Keep this clone folder where it is;
    # don't delete/move it after installing, or the app breaks.
    ln -sf "$SCRIPT_DIR/cinnamon-presets.py" "$BIN_DIR/cinnamon-presets"
    chmod 755 "$SCRIPT_DIR/cinnamon-presets.py"
else
    # No .git here (e.g. downloaded as a zip) -- plain copy, same as
    # before. Self-update won't be available for this install; the app
    # already handles that gracefully (falls back to the releases page).
    install -m 755 "$SCRIPT_DIR/cinnamon-presets.py" "$BIN_DIR/cinnamon-presets"
fi
install -m 644 "$SCRIPT_DIR/icons/cinnamon-presets.svg" "$ICON_DIR/cinnamon-presets.svg"
# Also under scalable/apps -- see debian/rules for why both locations matter.
install -m 644 "$SCRIPT_DIR/icons/cinnamon-presets.svg" "$SCALABLE_ICON_DIR/cinnamon-presets.svg"
install -m 755 "$SCRIPT_DIR"/helpers/*.sh "$HELPERS_DIR/"
# CHANGELOG.md, read at runtime for the one-time "what's new" popup after
# an update. For a git checkout this is already a sibling of the script
# itself (found there first, see _app_data_dir_candidates() in the app),
# but a plain copy install has no such sibling, so it's copied here too.
install -m 644 "$SCRIPT_DIR/CHANGELOG.md" "$SHARE_DIR/CHANGELOG.md"

# Custom hand-drawn category icons (Save/Export/Apply checklist rows) --
# optional, only copies whatever's actually been drawn so far. See
# icons/categories/ in the source tree for naming convention.
if compgen -G "$SCRIPT_DIR/icons/categories/*" > /dev/null 2>&1; then
    install -m 644 "$SCRIPT_DIR"/icons/categories/* "$CATEGORY_ICONS_DIR/"
fi

# Custom UI icons (toolbar/action glyphs, see UI_ICON_DIR_CANDIDATES) --
# same "copy whatever exists so far" behavior, empty today.
if compgen -G "$SCRIPT_DIR/icons/ui/*" > /dev/null 2>&1; then
    install -m 644 "$SCRIPT_DIR"/icons/ui/* "$UI_ICONS_DIR/"
fi

# Point the .desktop file's Exec at the installed binary and drop it in place.
sed "s|^Exec=.*|Exec=$BIN_DIR/cinnamon-presets|" \
    "$SCRIPT_DIR/cinnamon-presets.desktop" > "$APPS_DIR/cinnamon-presets.desktop"
chmod 644 "$APPS_DIR/cinnamon-presets.desktop"

# Refresh caches so the app shows up in the menu with its icon right away.
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

echo "Done. Launch it from the menu as 'Cinnamon Presets', or run: cinnamon-presets"
echo "(Make sure $BIN_DIR is on your PATH if running from a terminal.)"
