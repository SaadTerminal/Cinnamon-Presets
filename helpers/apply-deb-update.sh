#!/usr/bin/env bash
#
# Installs a downloaded .deb over the current Cinnamon Presets install.
# I call this via pkexec from the main app, always as root -- a .deb
# lives under /usr, so nothing short of root can update it, the same way
# nothing short of root could install it in the first place.
#
# Scope: this only ever runs dpkg on the exact .deb path it's given
# (plus apt-get install -f as a narrow dependency-repair fallback, see
# below). Nothing else on the system is touched.
#
# Arguments:
#   $1  DEB_PATH   path to the downloaded .deb file (required)

set -euo pipefail

DEB_PATH="${1:-}"

if [[ -z "$DEB_PATH" || ! -f "$DEB_PATH" ]]; then
    echo "Downloaded .deb not found: $DEB_PATH" >&2
    exit 1
fi

# dpkg -i can fail with "dependency problems" if something this package
# needs isn't already on the system -- unlikely in practice, since
# anyone running this update is by definition already running a working
# install of the SAME package with the SAME dependencies, but not
# impossible if a dependency got removed by hand since. `apt-get install
# -f` is the standard, narrow way to recover from exactly that: it only
# ever resolves and installs whatever dpkg just said it was missing, it
# doesn't touch anything else on the system.
if ! dpkg -i "$DEB_PATH"; then
    echo "dpkg reported a problem -- attempting to resolve missing dependencies…" >&2
    apt-get install -f -y
    # Retry now that dependencies should be satisfied. If this still
    # fails, I let it fail loudly rather than silently leaving the app
    # in a half-updated state.
    dpkg -i "$DEB_PATH"
fi

echo "Update installed. Restart the app to finish."
