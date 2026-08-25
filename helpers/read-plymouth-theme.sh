#!/usr/bin/env bash
# Read-only fallback for detecting the current Plymouth theme. Run via
# pkexec ONLY when the unprivileged detection methods (update-alternatives
# --query, plymouth-set-default-theme, reading the symlink/config file
# directly) all fail on a given system. This script never writes or
# changes anything — it only reports a theme name on stdout.
set -euo pipefail

# Preferred: the standard Debian/Ubuntu/Mint alternatives registry.
if command -v update-alternatives >/dev/null 2>&1; then
    VALUE="$(update-alternatives --query default.plymouth 2>/dev/null | awk -F': ' '/^Value:/{print $2}')"
    if [[ -n "$VALUE" ]]; then
        basename "$(dirname "$VALUE")"
        exit 0
    fi
fi

# Fall back to the tool itself, now guaranteed to be root and on a
# proper PATH.
if command -v plymouth-set-default-theme >/dev/null 2>&1; then
    THEME="$(plymouth-set-default-theme 2>/dev/null || true)"
    if [[ -n "$THEME" ]]; then
        echo "$THEME"
        exit 0
    fi
fi

# Last resort: read the alternatives symlink directly.
if [[ -L /etc/alternatives/default.plymouth ]]; then
    TARGET="$(readlink -f /etc/alternatives/default.plymouth)"
    if [[ -n "$TARGET" ]]; then
        basename "$(dirname "$TARGET")"
        exit 0
    fi
fi

echo "Could not determine the current Plymouth theme on this system." >&2
exit 1
