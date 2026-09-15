#!/usr/bin/env bash
#
# Read-only fallback for figuring out which Plymouth theme is currently
# active. The main app tries this ONLY when its own unprivileged
# detection methods -- reading `update-alternatives --query` without
# root, calling plymouth-set-default-theme with no arguments, reading the
# alternatives symlink or config file directly -- have all already
# failed on a given system.
#
# This script never writes or changes anything on the system. It only
# ever reports a theme name on stdout, or fails with nothing printed. I
# still run it via pkexec (so it IS root when it runs), purely because
# some systems restrict reading certain alternatives/plymouth state to
# root -- root access here is about being ABLE to read the state, not
# about needing to change anything.

set -euo pipefail

# Preferred: the standard Debian/Ubuntu/Mint alternatives registry. This
# is the same mechanism apply-plymouth.sh writes through, so reading it
# back here is the most direct, most reliable source of truth for
# "what's actually selected right now".
if command -v update-alternatives >/dev/null 2>&1; then
    VALUE="$(update-alternatives --query default.plymouth 2>/dev/null | awk -F': ' '/^Value:/{print $2}')"
    if [[ -n "$VALUE" ]]; then
        # $VALUE is a full path to the winning alternative's .plymouth
        # file (e.g. /usr/share/plymouth/themes/<name>/<name>.plymouth)
        # -- the theme name is just its parent directory's name.
        basename "$(dirname "$VALUE")"
        exit 0
    fi
fi

# Fall back to the tool itself. Calling this with no arguments prints the
# current theme rather than setting one -- and now that this script is
# guaranteed to be running as root with a proper PATH, it has a better
# chance of working than it did when the main app first tried it
# unprivileged.
if command -v plymouth-set-default-theme >/dev/null 2>&1; then
    THEME="$(plymouth-set-default-theme 2>/dev/null || true)"
    if [[ -n "$THEME" ]]; then
        echo "$THEME"
        exit 0
    fi
fi

# Last resort: read the alternatives symlink directly off disk, bypassing
# both tools entirely. If update-alternatives itself isn't installed (or
# is behaving oddly) this is the most primitive thing that can still work.
if [[ -L /etc/alternatives/default.plymouth ]]; then
    TARGET="$(readlink -f /etc/alternatives/default.plymouth)"
    if [[ -n "$TARGET" ]]; then
        basename "$(dirname "$TARGET")"
        exit 0
    fi
fi

# Every method above failed -- I genuinely don't know the current theme
# on this system, and I'd rather say so clearly than guess.
echo "Could not determine the current Plymouth theme on this system." >&2
exit 1
