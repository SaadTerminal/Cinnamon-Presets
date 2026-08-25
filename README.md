# Cinnamon Presets

**BETA-0.9**

A desktop-preset manager for **Linux Mint Cinnamon** — save your whole
desktop "look" as one named preset, and switch between them the way
Windows XP switched between visual styles.

A preset now covers:

- GTK theme, the **Cinnamon shell theme** (panel/menu/calendar — labeled
  "Desktop" in Cinnamon Settings, a separate theme from GTK), icon theme,
  cursor theme (+ cursor size), sound theme
- Wallpaper
- Panel layout, applet placement, and each applet's own settings;
  desklets and extensions
- Per-app icon/launcher overrides (e.g. an app you gave a custom icon)
- Optionally: LightDM login screen, Plymouth boot splash, GRUB bootloader
  (**GRUB is untested — see below**)

### BETA-0.9 changes (Roadmap Phase 3 — Data Model + Main List Rebuild)

- **New meta.json fields:** `name` (mirrors the folder name, kept in
  sync on rename), `description` (empty until Phase 4's Save wizard can
  set it), `saved_at` (powers the new date sort), and `categories` — a
  computed status for all 11 mockup categories (`present` /
  `not_applicable` / `not_implemented` / `error`, plus
  `skipped_on_purpose` reserved for Phase 4's opt-out checkboxes).
  Deliberately honest about **Profile Picture**: there's no
  AccountsService code anywhere in this app yet, so it's always reported
  `not_implemented` rather than pretending it's tracked.
- Presets saved before this version are normalized on read, not
  rewritten on disk — same non-destructive approach as the Phase 1
  legacy-apply fallback.
- **Main window rebuilt** around a file-manager-style list: grid/list
  toggle, thumbnail-size slider (grid mode), search (matches name +
  description), sort by Name or Date Saved.
- Every preset now shows a real thumbnail — its saved screenshot if it
  has one, otherwise a **deterministic gradient placeholder** generated
  from a hash of its name, so nothing renders as a blank tile, including
  presets saved before Phase 2's screenshot capture existed.
- Apply/Rename/Delete/System-Boot-Settings gray out until a preset is
  actually selected; renaming, saving, and capturing a screenshot all
  reselect the affected preset afterward instead of dropping the
  selection.
- **New dependency: `python3-cairo`** (draws the gradient placeholders).
  Added to the requirements list below.

### BETA-0.8 changes

- **LightDM's `background=` image is now bundled**, not just the config
  file that references it. `/etc/lightdm/slick-greeter.conf` points at
  an absolute path (e.g. `/usr/share/backgrounds/.../nikki.png`) — the
  greeter runs before the user's own session exists, so if that file
  ever moved or got deleted, the preset was silently pointing at
  nothing. Same class of bug the desktop wallpaper handling already
  solved, just not applied to LightDM. Fixed the same way: the
  referenced image is copied into the preset at save time, and on apply
  it's installed to an app-managed path
  (`/usr/share/backgrounds/cinnamon-presets/<preset-name>.<ext>`) and
  the config is rewritten to point there — so it no longer depends on
  the original file surviving. A plain solid-color `background=#hex`
  (no file involved) is left alone, correctly not "bundled."
- The System Boot Settings dialog's LightDM row now says explicitly
  whether a background image was bundled, missing at save time, or
  there was nothing to bundle (solid color) — not just "Saved."

**If you saved presets before BETA-0.8, re-save them** — the old ones
never captured the background image, so applying one will still fall
back to LightDM's own default background even after this fix, since
there's nothing bundled to restore.

### BETA-0.7 changes (Roadmap Phase 2 — Screenshot Capture Module)

- New standalone screenshot capture flow: hides the app, shows a short
  on-screen countdown (~4s, enough time to open the Cinnamon menu or
  arrange a window), captures the whole screen straight through GDK
  (no `gnome-screenshot`, no other external screenshot tool), then
  shows a preview with **Retake** / **Keep**. Nothing is written to
  disk until you hit Keep.
- Wired in as an **optional** follow-up right after saving a new
  preset — decline it and a preset saves exactly as before. This is
  deliberately not mandatory yet: the roadmap's Save wizard (Phase 4)
  is what makes a screenshot a required part of saving, and it reuses
  this same module rather than reimplementing capture. The main
  preset list also doesn't show thumbnails yet — that's Phase 3.
- Every preset's `meta.json` now has a `"screenshot"` field
  (`{"status": "none"}` if you skip it, `{"status": "saved", "file":
  "screenshot.png"}` if you keep one), so later phases have one
  consistent thing to check.
- Fixed the countdown badge itself getting captured in the screenshot
  — the capture now waits for the compositor to actually redraw after
  the countdown window closes, instead of grabbing the very next
  frame.
- The mouse cursor is never in the base capture. The Retake/Keep dialog
  now has a **"Show mouse cursor in screenshot"** checkbox — off by
  default — that composites the current cursor-theme glyph onto the
  preview (and the saved file, if you keep it) at wherever the pointer
  actually was. No extra dependency: it's GDK's own cursor pixbuf, not
  an XFixes/X11 hack.

### BETA-0.6 changes (verified against a live Cinnamon 6.6.9 machine)

BETA-0.5's dconf allowlist was written from public schema docs and never
checked against a real `dconf dump`. It didn't error — `dconf write`/
`dconf read` don't validate against schemas — it just silently touched
the wrong key, or a dead one, or nothing. Fixed:

- **The Cinnamon shell theme was never captured at all.** It's a
  genuinely separate setting from `gtk-theme` — `org.cinnamon.theme`'s
  `name` key (`/org/cinnamon/theme/name`), confirmed against Mint's own
  `cs_themes.py`. Now part of the Style category and bundled as an asset
  like the GTK/icon/cursor themes already were.
- `panel-autohide` → `panels-autohide` (real key is plural; the old one
  was a silent no-op).
- `panel-resizable` → `panels-resizable` (same mistake, same fix).
- `panel-scale-text-icons` → `panels-scale-text-icons`. The singular key
  does exist but is explicitly marked deprecated/inert in Cinnamon's own
  schema — it was being written to a key nothing reads.
- Dropped `panel-launchers` — marked "Obsolete - unused" upstream.

**If you saved presets on BETA-0.5, re-save them** — the old ones are
missing the Cinnamon shell theme entirely and have the three dead panel
keys baked in as legacy per-category data.

### BETA-0.5 changes (Roadmap Phase 1 — foundation)

- **Explicit dconf allowlist, replacing the whole-tree reset/load.**
  `/org/cinnamon/` also holds things that have nothing to do with
  "theme" — favorite-apps, custom keybindings — so applying a preset
  used to silently roll those back to whatever they were at save time
  too. Now only specific, named keys/directories are ever read, reset,
  or written, split into 8 categories (Style, Cursor, Icons, Fonts,
  Sounds, Wallpaper, Panel Modifications, Widgets) — see
  `CATEGORY_DCONF_KEYS`/`CATEGORY_DCONF_DIRS` in `cinnamon-presets.py`
  for the exact list.
- **Fault-isolated Apply.** One theme failing to copy, one addon being
  unreadable, or one dconf category failing to write no longer aborts
  the rest — every step is independent, every failure is reported, and
  Apply only fails outright if literally nothing could be applied.
- Presets saved before BETA-0.5 still apply correctly (a legacy
  fallback path handles the old whole-tree format), with a note
  suggesting a re-save to move them onto the safer, scoped format.
- Addon bundling is now explicitly mapped to its matching category
  (extensions → Style, applets → Panel Modifications, desklets →
  Widgets), laying groundwork for the per-category Save/Export/Apply
  checklists planned next.

> **Heads up for anyone testing this:** the exact dconf key names in the
> new allowlist are standard, publicly-documented Cinnamon GSettings
> paths, not verified against a live `dconf dump /org/cinnamon/` on real
> hardware. Please diff that dump against `CATEGORY_DCONF_KEYS` /
> `CATEGORY_DCONF_DIRS` before trusting this with anything you can't
> afford to lose — a key name could have shifted slightly between
> Cinnamon 5.x and 6.x.

### BETA-0.4 changes

- Fixed the actual cause of Plymouth theme detection coming up empty:
  `plymouth-set-default-theme` lives in `/usr/sbin`, off a GUI session's
  PATH. Detection now tries `update-alternatives --query
  default.plymouth` first (usually on PATH, no root, and the real
  mechanism Mint/Ubuntu/Debian register the theme through), then falls
  back through several other methods. If every unprivileged method still
  fails on your system, the app will offer a one-time, separately
  authorized, read-only root check — see below.
- Applying a Plymouth theme now sets it via `update-alternatives --set
  default.plymouth` (the same thing `update-alternatives --config
  default.plymouth` edits), then always explicitly runs
  `update-initramfs -u` afterward.
- Fixed a regression: an unhandled error partway through saving (in the
  new panel-layout bundling, or in LightDM/Plymouth/GRUB) could abort the
  save before anything was written to disk — silently discarding the
  wallpaper and theme/addon data that had already been captured in that
  same save. Every optional save step is now isolated so one failing
  can't cost the others.
- New: per-app icon/launcher overrides (changing a single app's icon via
  the menu editor) are now bundled and restored. These live as override
  `.desktop` files under `~/.local/share/applications/`, entirely outside
  dconf, so they weren't covered before.
- New: panel/applet layout is now part of every preset, including each
  applet's own settings (not just which applets are enabled and where).
- GRUB support is marked **untested** in the System Boot Settings dialog.
  It hasn't been verified end-to-end — use with caution.

### If saving Plymouth still needs admin rights on your system

A few systems restrict reading the current Plymouth theme even to the
owning user. If that's the case here, saving a preset will pop up a
separate confirmation asking to check the theme with a one-time
`pkexec` prompt — distinct from every other admin action in this app,
read-only, and not tied to Apply. Declining just means that preset saves
without a Plymouth theme, same as before. No credentials are cached
either way — saving another preset later asks again.

For any custom (non-stock) theme, extension, applet, or desklet, the
actual files are bundled into the preset — not just their names — so the
preset still works after a fresh install or on another machine, even if
the original files are gone.

## How it works

Almost all of Cinnamon's own state lives under one dconf tree,
`/org/cinnamon/` — this includes GTK/icon/cursor/sound theme names, cursor
size, wallpaper path, and the enabled extensions/applets/desklets list.
Saving a preset is `dconf dump /org/cinnamon/`, plus:

- a copy of the current wallpaper image
- for any GTK/icon/cursor/sound theme installed under your home folder
  (not a stock system theme), a copy of that theme's files
- for any extension/applet/desklet installed under your home folder, a
  copy of its files
- for each currently-enabled applet, a copy of its own settings folder
  (`~/.cinnamon/configs/<uuid>/`) — applet placement/order is already in
  the dconf dump, but per-applet settings like a Weather applet's chosen
  city live outside dconf, as JSON files, so they need their own copy
- a copy of every per-app icon/launcher override in
  `~/.local/share/applications/` (e.g. an app whose icon you changed via
  the menu editor), plus any custom icon image file it points to by
  absolute path — none of this is dconf either
- a read-only snapshot of your LightDM greeter config, Plymouth theme,
  and GRUB config, if present (no admin rights needed just to *read*
  these on most systems — see the note above if yours needs them anyway)

Applying a preset (the normal **Apply** button) resets `/org/cinnamon/`,
loads the saved dump back in, restores any bundled theme/extension files,
rewrites the wallpaper path, and asks the running Cinnamon shell to
reload — no logout required, no admin rights needed.

### System Boot Settings (LightDM / Plymouth / GRUB)

These three are **not** touched by the normal Apply button. They're boot-
and login-critical, so they live in their own dialog
(**"System Boot Settings…"**) with one Apply button per item. Each button:

- shows a confirmation before doing anything
- triggers its own separate `pkexec` (admin authentication) prompt
- runs a small, narrowly-scoped helper script that only touches that one
  thing — the GRUB helper can't touch LightDM's config, the LightDM
  helper can't touch GRUB's, etc.
- backs up the file it's replacing before overwriting it
  (`<file>.cinnamon-presets-backup`)

This means authorizing one of them never grants the app blanket root
access — you're asked, and scoped, per action, every time.

> **Heads up on GRUB specifically: this is untested.** It hasn't been
> verified end-to-end yet, and it's shown in red in the app for that
> reason. Applying it runs `update-grub`, which regenerates your actual
> boot menu. Double check you're applying the preset you mean to, and
> double check your system boots correctly afterward. A backup of the
> previous `/etc/default/grub` is kept, but you'd need to restore it
> manually
> (`sudo cp /etc/default/grub.cinnamon-presets-backup /etc/default/grub && sudo update-grub`)
> if something goes wrong.

Presets are stored in `~/.config/cinnamon-presets/presets/`, completely
separate from wherever the app itself gets installed. **Uninstalling or
reinstalling the app never touches your saved presets.**

## Requirements

Already installed by default on Linux Mint Cinnamon:

- `python3-gi`, `gir1.2-gtk-3.0`, `python3-cairo`, `dconf-cli`
- `policykit-1` (provides `pkexec`, used only for the System Boot
  Settings dialog)
- `plymouth`, `grub2-common` (standard on Mint)
- `git` (only needed for the in-app updater)

## Installing

```bash
git clone <repo-url-goes-here>
cd cinnamon-presets
./install.sh
```

This installs the app to `~/.local/bin/cinnamon-presets`, the pkexec
helper scripts to `~/.local/share/cinnamon-presets/helpers/`, adds a menu
entry, and drops in a placeholder icon. None of this needs root — the
only admin prompts you'll ever see come later, inside the app, when you
explicitly apply something from System Boot Settings.

You can also run it directly without installing:

```bash
chmod +x cinnamon-presets.py
./cinnamon-presets.py
```
(When run this way, it looks for the helper scripts in a `helpers/`
folder next to the script itself, so keep the folder structure intact.)

## Uninstalling

```bash
./uninstall.sh
```

By default this only removes the app itself (binary, helper scripts,
`.desktop` entry, icon) — your saved presets in
`~/.config/cinnamon-presets/` are left alone.

If you actually want your saved presets deleted too:

```bash
./uninstall.sh --purge
```

## Updating

The app has a built-in **"Check for Updates"** button that checks this
repo's GitHub releases. If you installed via `git clone`, clicking
"Update" runs `git pull` in place and asks you to restart the app.
Otherwise it opens the release page in your browser.

> Note for maintainers: `GITHUB_REPO_URL` near the top of
> `cinnamon-presets.py` needs to be set to the real repo URL for the
> update checker to work — it's currently a placeholder.

## Usage

1. Set up your desktop exactly how you want it.
2. Open Cinnamon Presets → **"+ Save Current Desktop As New Preset"** →
   give it a name. (This also silently captures LightDM/Plymouth/GRUB
   state, read-only, no prompts.)
3. Select a saved preset and hit **Apply** for the desktop-level stuff.
4. If you also want the login screen / boot splash / bootloader from that
   preset, open **"System Boot Settings…"** and apply each one you want,
   individually.

## Known limitations / roadmap ideas

- **The Cinnamon Settings app doesn't refresh its own displayed values**
  if you already have it open when you apply a preset — close and reopen
  it to see correct values. This is a Cinnamon Settings limitation, not
  something this app can fix.
- LightDM support currently assumes **slick-greeter** (Mint's default).
  Other greeters (lightdm-gtk-greeter, etc.) aren't handled yet.
- No thumbnail previews yet (just a name list).
- Only covers Cinnamon settings under `/org/cinnamon/`. Nemo (file
  manager) preferences and terminal profiles live under separate schemas
  and aren't captured yet.
- Applying a preset restarts the Cinnamon shell (a couple seconds of
  flicker) — expected and safe.
- The admin prompts for LightDM/Plymouth/GRUB currently show a generic
  pkexec authentication message. A proper Polkit `.policy` file (installed
  under `/usr/share/polkit-1/actions/`) could give each one a custom
  description and the app's icon — left for a later version since it
  needs its own root step during install.
- Placeholder icon — swap out `icons/cinnamon-presets.svg` for real
  artwork before a wider release.
- No author/credit info yet — will be added once the author's public
  profile/social links exist.
- Possible future: Flathub packaging. This is inherently
  Cinnamon-specific, and the LightDM/Plymouth/GRUB features need real
  root access to `/etc` and `/boot` outside any sandbox, so Flatpak
  packaging would need significant extra permission work — a "someday"
  item, not a near-term one.

## License

MIT — do whatever you want with it.
