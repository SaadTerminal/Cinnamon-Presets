#!/usr/bin/env bash
#
# Builds a lightweight AppImage of Cinnamon Presets -- relies on the
# system's own python3-gi/GTK3/cairo rather than bundling a separate
# runtime (see AppRun's own comment for why). Run this from anywhere;
# it finds the project root relative to its own location.
#
# Requires: appimagetool on PATH, or set APPIMAGETOOL to its path.
# Output: Cinnamon-Presets-<version>-x86_64.AppImage, in the directory
# this script is run from.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

VERSION="$(grep -oP '(?<=^VERSION = ")[^"]+' "$PROJECT_ROOT/cinnamon-presets.py")"
if [[ -z "$VERSION" ]]; then
    echo "Couldn't read VERSION from cinnamon-presets.py" >&2
    exit 1
fi

APPIMAGETOOL="${APPIMAGETOOL:-appimagetool}"
if ! command -v "$APPIMAGETOOL" >/dev/null 2>&1; then
    echo "appimagetool not found on PATH (set APPIMAGETOOL=/path/to/it, or" >&2
    echo "download one from https://github.com/AppImage/appimagetool/releases)." >&2
    exit 1
fi

BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT
APPDIR="$BUILD_DIR/AppDir"

# Same file layout as the .deb (see ../../debian/rules), just rooted at
# the AppDir instead of /usr -- kept in sync by hand since these are two
# genuinely different build systems, not because either one is derived
# from the other.
install -d "$APPDIR/usr/bin"
install -m 755 "$PROJECT_ROOT/cinnamon-presets.py" "$APPDIR/usr/bin/cinnamon-presets"

install -d "$APPDIR/usr/share/cinnamon-presets/helpers"
install -m 755 "$PROJECT_ROOT"/helpers/*.sh "$APPDIR/usr/share/cinnamon-presets/helpers/"

install -d "$APPDIR/usr/share/icons/hicolor/128x128/apps"
install -m 644 "$PROJECT_ROOT/icons/cinnamon-presets.svg" "$APPDIR/usr/share/icons/hicolor/128x128/apps/"

# Also under scalable/apps -- see ../../debian/rules for why both locations matter.
install -d "$APPDIR/usr/share/icons/hicolor/scalable/apps"
install -m 644 "$PROJECT_ROOT/icons/cinnamon-presets.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/"

if compgen -G "$PROJECT_ROOT/icons/categories/*" > /dev/null 2>&1; then
    install -d "$APPDIR/usr/share/cinnamon-presets/icons/categories"
    install -m 644 "$PROJECT_ROOT"/icons/categories/* "$APPDIR/usr/share/cinnamon-presets/icons/categories/"
fi

# Custom UI icons (toolbar/action glyphs, see UI_ICON_DIR_CANDIDATES) --
# same "copy whatever exists so far" behavior, empty today.
if compgen -G "$PROJECT_ROOT/icons/ui/*" > /dev/null 2>&1; then
    install -d "$APPDIR/usr/share/cinnamon-presets/icons/ui"
    install -m 644 "$PROJECT_ROOT"/icons/ui/* "$APPDIR/usr/share/cinnamon-presets/icons/ui/"
fi

# CHANGELOG.md, read at runtime for the one-time "what's new" popup after
# an update (see get_changelog_entries_since() in the app).
install -m 644 "$PROJECT_ROOT/CHANGELOG.md" "$APPDIR/usr/share/cinnamon-presets/CHANGELOG.md"

# AppImage's own required layout: a .desktop file and an icon, both at
# the AppDir root (not under usr/share the way the "real" installed
# copies above are) -- this is what appimagetool itself looks for, and
# what desktop integration tools read when the AppImage is run directly.
install -m 644 "$PROJECT_ROOT/cinnamon-presets.desktop" "$APPDIR/cinnamon-presets.desktop"
install -m 644 "$PROJECT_ROOT/icons/cinnamon-presets.svg" "$APPDIR/cinnamon-presets.svg"
install -m 755 "$SCRIPT_DIR/AppRun" "$APPDIR/AppRun"

OUTPUT="Cinnamon-Presets-${VERSION}-x86_64.AppImage"
VERSION="$VERSION" ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUTPUT"

echo "Built $OUTPUT"
