#!/usr/bin/env python3
"""
Cinnamon Presets — desktop preset manager for Linux Mint Cinnamon.

Saves and restores full "look" presets: GTK theme, icon theme, cursor
theme, cursor size, wallpaper, panel layout/applets, extensions,
desklets, and sound theme — all in one switchable snapshot, the way
Windows XP handled visual styles.

BETA-0.18 (bug fixes) adds:
  - Fixed a real, broader-than-reported bug: find_asset_dir() judged
    whether a GTK/icon/cursor theme was "stock, safe to skip bundling"
    purely from its directory path (/usr/share/... = assumed stock).
    That's wrong — a custom theme manually installed under
    /usr/share/themes/ (common when someone `sudo cp`s a downloaded
    theme in, rather than putting it in ~/.themes) looked identical to
    an actual Mint-shipped one and silently never got bundled. New
    _is_dpkg_managed() replaces the path guess with an actual
    `dpkg -S` ownership check — the real question ("was this installed
    by the package manager") instead of guessing from where it happens
    to sit. Defaults to "bundle it" whenever dpkg can't answer (not on
    PATH, query fails), since under-bundling silently breaks a look and
    over-bundling just costs a bit of disk space — the safe direction to
    default toward isn't a close call. Fixes this for the desktop
    session's own theme AND, via reuse, for LightDM below.
  - Reported bug, now fixed: save_lightdm() only ever inspected
    slick-greeter's `background` key — never theme-name/icon-theme-name/
    cursor-theme-name, its own separate theme selection for the login/
    lock screen (can differ from the desktop session's). A custom one
    installed system-wide (LightDM can't read a regular user's
    ~/.themes anyway) was never bundled, so it silently broke the
    moment the original system-wide copy was gone. Now bundled the same
    way the background image already was, using the fixed
    find_asset_dir() above. apply_lightdm() passes the bundled asset
    dirs to apply-lightdm.sh (updated) positionally; ${var:?} guards
    added there so an accidentally-empty root/name fails loudly instead
    of `rm -rf` silently expanding too broad, since this runs as root.
    ApplyPresetDialog's LightDM status text updated to report bundled
    theme/icon/cursor assets, not just the background.

BETA-0.17 (Roadmap Phase 9 — Settings Tab, plus a couple of loose ends)
adds:
  - Fixed the inconsistent main-list deselection bug: clicking empty
    space only worked when the click happened to land in genuinely
    unclaimed area, since a FlowBoxChild's hit area is its whole grid
    cell, not just the visible thumbnail -- most "visually empty" space
    around a tile was still technically on that child. Clicking a tile
    that's already selected now reliably toggles it off, which has no
    such coordinate ambiguity.
  - New: preset migration. migrate_preset()/migrate_all_presets() run
    automatically at startup, upgrading any preset's meta.json to the
    current schema in place -- including reparsing a legacy whole-tree
    cinnamon.dconf dump directly into the new per-category format, using
    the same allowlist _dump_category() uses on a live system. No live
    desktop state needed, so this works even if the current desktop
    looks nothing like the preset being migrated. Idempotent, stamped
    with schema_version so it's a no-op after the first run.
  - New Settings window (Gtk.Stack + Gtk.StackSidebar, six sections):
    - General: default grid/list view, default thumbnail size, default
      sort order -- actually wired into the main window's own startup
      state now, not just stored.
    - Diagnostics: the stray GTK-override check, always available here
      (not just the reactive Apply-time banner); a new rotating log file
      (5MB x 3 backups) with every save/apply/pkexec-helper/update-check
      outcome logged, a global exception hook, "Open Log File," and
      "Copy Diagnostic Info" for lower-friction bug reports; a manual
      "Re-run Migration Now."
    - Storage: apparent disk usage of ~/.config/cinnamon-presets via a
      custom three-segment Cairo bar (GTK has no built-in widget for
      "three quantities summing to a total"), a hybrid low-space warning
      (min(10% of capacity, 30GB)), Open Presets Folder, and a Danger
      Zone with Erase All Data and a native-Python Uninstall (kept in
      sync with uninstall.sh's own target paths, since that script isn't
      guaranteed to still be on disk by the time someone clicks an
      in-app button). Neither ever touches home-directory theme folders
      or root-owned system paths -- a look installed via a preset
      survives removing the app or its data, same as before. Both
      confirmation dialogs' actual destructive button (Erase All Data /
      Uninstall / Delete Everything) is styled destructive-action (red);
      "Export Presets First" stays plain so it doesn't visually compete
      with the destructive option, and Erase All Data got the same
      export-first prompt Uninstall's purge path already had.
    - Backups (b-lite): "Restore Previous Configuration" used to be
      GRUB-only in the Apply dialog; now LightDM and Plymouth have it
      too, both here and in ApplyPresetDialog. LightDM needed a new
      restore-lightdm.sh helper (mirrors the existing GRUB one). Plymouth
      was the addendum's flagged open question -- resolved without
      touching apply-plymouth.sh at all: the app now records whichever
      theme is active right before an apply changes it, then "restore"
      re-applies that recorded name through the same existing helper.
    - Updates: moved in from the footer button; manual Check Now, current
      version, throttle explanation.
    - About: fixed a real bug found while moving this over -- the old
      dialog claimed "Licensed under MIT," which was wrong, this app is
      GPLv3. Now shows a plain-English GPLv3 summary plus a link to the
      actual LICENSE file on GitHub. Footer Patreon/YouTube/GitHub links
      now use real brand icons (icons/ui/<name>.svg) instead of plain
      text buttons, gracefully degrading to text if those files aren't
      in place yet.

BETA-0.16 (Roadmap Phase 8 — Update System) adds:
  - Silent, throttled startup check: a small state file
    (~/.config/cinnamon-presets/update_check_state.json) records the last
    check time, and the app only auto-checks again after
    UPDATE_CHECK_INTERVAL_SECONDS (6h, roadmap's "every few hours") has
    passed. Runs 2s after the window opens (so it doesn't compete with
    first paint) and entirely on a background thread. The "Check for
    Updates" button (still on the main window until Phase 9 moves it
    into Settings) always bypasses the throttle and checks immediately,
    same as the roadmap specifies.
  - Replaced the blocking Yes/No modal for "update available" with a
    slim Gtk.InfoBar banner across the top of the window — visible only
    when there's actually something to say, closable, with its own
    "Update Now" button. A silent background check that finds nothing
    new (or fails, or hits an unconfigured repo URL) says nothing at
    all; only the manual button's check surfaces those as a status
    message or dialog, since only that one was something the person
    explicitly asked for.
  - Self-update (perform_git_update(), unchanged) now finishes with an
    actual in-place restart — new restart_process() calls os.execv() to
    replace the running process image with a fresh launch of the
    now-updated script, rather than telling the person to close and
    reopen the app themselves. Never returns on success, by design.
  - AppImage awareness: running under $APPIMAGE is now detected
    (_is_appimage()) so the manual-update-needed fallback message says
    so plainly ("in-place self-update for that isn't wired up yet")
    instead of the generic, slightly-wrong-sounding "not a git
    checkout" message. No actual AppImage download-and-swap logic yet —
    the roadmap marks that whole distribution path optional/future/
    secondary, and there's no build system producing one yet to
    download in the first place.

BETA-0.15 (Roadmap Phase 7 — GRUB Safety Upgrade) adds:
  - New GrubCooldownDialog: applying GRUB now goes through a forced,
    non-privileged ~18s cooldown (roadmap's "~15-20s") showing what's
    about to change, before the Continue button enables and turns red
    (GTK's "destructive-action" style class) — replacing the plain
    Yes/No confirm every other boot item still uses. Nothing in this
    dialog touches the system or requests root; it exists purely so a
    rushed click can't skip past it. The real pkexec prompt (via the
    existing apply_grub()/apply-grub.sh) only becomes reachable after
    Continue is actually clicked.
  - New "Restore Previous Config" button on the GRUB row: restores
    /etc/default/grub from the backup apply-grub.sh has always created
    before every overwrite (grub.cinnamon-presets-backup — this button
    exposes an existing safety net, not a new one), then reruns
    update-grub. New restore-grub.sh helper, same narrow-scope
    convention as every other pkexec helper here. Not tied to any one
    preset — undoes this app's own most recent GRUB apply, the way an
    "undo" should work rather than requiring the person to remember
    which preset they applied last. Only shown when a backup actually
    exists; refreshed after every GRUB apply/restore rather than only
    computed once when the dialog opens. Deliberately a plain Yes/No
    confirm, not the same cooldown as applying — restoring undoes this
    app's own change, it doesn't introduce a new unfamiliar config.
  - GRUB's "⚠ UNTESTED" warning is UNCHANGED and deliberately so: the
    roadmap is explicit that flag only comes off after independent
    real-hardware testing, not when the phase's checklist items are
    built. Still marked experimental in-UI.

BETA-0.14 (Roadmap Phase 6, part 2 — Import) adds:
  - New import_preset(): extracts a .tar.gz preset archive (the same
    shape export_preset() writes) into PRESETS_DIR/<name>/. Mirrors
    export's safety shape rather than inventing a new one: staged
    extract into a private tempfile.mkdtemp(dir=PRESETS_DIR) directory
    (same filesystem, so the final commit is one instant os.rename(),
    not a copy), file-by-file extraction (not tarfile.extractall()) for
    real progress and a safe mid-operation cancel, reusing
    run_export_with_progress()'s dialog rather than a second
    cancel-aware mechanism. Structurally enforces "never auto-applies
    anything" from the roadmap -- this module only ever writes files to
    disk; nothing in it calls anything from the apply-side code at all.
  - New _peek_archive_name(): reads just the archive's member list (no
    extraction) to find its top-level preset name, so the GUI can check
    for a name collision and ask *before* running the real extraction,
    not discover the conflict only at the final rename. A collision
    prompts for a different name via the same _ask_name() dialog Rename
    already uses; declining leaves everything untouched.
  - Path-traversal defense on every extracted member (checked against
    the staging directory before extraction) plus Python 3.12's
    tarfile "data" extraction filter where available (falls back
    cleanly on older Python) -- confirmed by an automated test with a
    deliberately malicious archive member (a "../../../etc/..." path)
    that verifies nothing gets written outside the staging directory.
  - Confirmed by automated tests (same GTK-free approach as Export's):
    a real symlink survives import intact; a name collision raises
    cleanly without touching the existing preset or leaving a staging
    directory behind; renaming during import updates meta.json's "name"
    field to match the new folder; cancelling mid-extraction and an
    archive missing meta.json both clean up their staging directory
    completely. The GTK Cancel-button wiring itself is NOT covered by
    an automated test, same caveat as Export.
  - "Import" button added next to Export in the main window (not
    selection-gated, same as "+ Save Current Desktop As New Preset") --
    opens a file chooser, then the same cancel-safe progress dialog.

BETA-0.13 (Roadmap Phase 6, part 1 — Export) adds:
  - New export_preset(): writes a preset out as a single-top-level-directory
    .tar.gz (not zip -- cursor themes rely on symlinks, and zipfile
    doesn't round-trip those on extract, tarfile does natively; confirmed
    with an automated test against a real symlink inside a fake theme
    folder -- GTK isn't needed for this, so it isn't just asserted).
    Safe staged write: writes to `<dest>.part` and only os.replace()s to
    the real filename on full success -- confirmed via automated tests
    covering both a pre-write cancellation and a mid-write exception,
    neither leaves a `.part` file behind.
  - Per-category checkbox selection at export time, reusing the same
    12-category checklist as Save/Apply via the same
    build_category_checklist_row() (see below) -- but a different default
    checkbox state, which is the actual safety model here: Lock Screen /
    Boot Animation / GRUB start unchecked, since export leaves the
    machine, and must be deliberately opted into. An unchecked category
    is both left out of the archive's files AND rewritten to
    "skipped_on_purpose" in the bundled meta.json -- reusing
    save_preset()'s own status shape (via new _redact_meta_for_export())
    rather than inventing a second mechanism, so a re-imported preset
    that had GRUB unchecked on export is indistinguishable from one that
    had it unchecked at save time. Also confirmed by automated test.
  - Export is blocked with a clear message if the preset has no
    screenshot yet (typically an import that hasn't been given one) --
    checked before the checklist dialog even opens, not after someone's
    already picked categories.
  - New run_export_with_progress(): a determinate-progress, Cancel-button
    sibling to run_with_progress() (which deliberately has neither, since
    nothing it's used for is safe to interrupt). Export only ever reads
    from PRESETS_DIR and writes to a throwaway .part file, so it's
    actually safe to cancel -- export_preset()'s own cancel_event handling
    is covered by the automated tests above; the dialog's Cancel button
    itself (GTK signal wiring) is NOT covered by an automated test and
    hasn't been exercised on a real desktop session yet.
  - Extracted build_category_checklist_row() out of SavePresetWizard and
    ApplyPresetDialog's separate near-identical _build_category_row()
    methods (the same duplication risk category_swatch_pixbuf() was
    already pulled out to avoid) before adding a third copy for
    ExportDialog. Also extracted show_message_dialog() out of
    ApplyPresetDialog's private _result_dialog().
  - New Export button on the main window, gated on selection like Apply/
    Rename/Delete.
  - Import (Phase 6 part 2) deliberately not part of this version --
    tackled as its own pass so Export could be finished and verified on
    its own first, per its own explicit complexity.

BETA-0.12 (Roadmap Addendum — Progress Indicators, retrofitted into
Phases 4 and 5; finishes Phase 5) adds:
  - New run_with_progress() helper: runs a slow function on a background
    thread instead of blocking the GTK main loop, with a small
    indeterminate progress dialog standing in for "the window looks
    crashed" while it works. No cancel button — nothing it's used for
    (a dconf load, a shutil.copytree, a pkexec call mid-authentication)
    is safe to interrupt partway through, so it doesn't pretend to offer
    that; Phase 6's Import/Export is expected to reuse this same dialog
    for its own genuinely cancel-safe operations rather than a second
    mechanism built from scratch.
  - Wired into the three places that were silently blocking the UI: the
    Save wizard's actual save_preset()/save_screenshot() work, Apply
    Theme's apply_preset() call, and each boot-item Apply
    (LightDM/Plymouth/GRUB)'s pkexec call individually. Plymouth's row
    gets its own progress message calling out the initramfs rebuild
    specifically, since it's the slowest and most likely to look hung.
  - This was the last item on Phase 5's checklist (see the roadmap
    addendum) — Phase 5 is done as of this version; Phase 6
    (Import/Export) starts next.

BETA-0.11 (Roadmap Phase 5 — Apply Flow Rebuild) adds:
  - ApplyPresetDialog fully replaces the old separate SystemBootDialog /
    "System Boot Settings…" button. Hitting "Apply" now opens one
    scrollable page per preset with independent, separately-authorized
    sections: Apply Theme (no root) plus Apply Lock Screen / Apply Boot
    Animation / Apply GRUB Bootloader (each root-gated, each its own
    pkexec call — authorizing one never grants access to the others).
    GRUB keeps its existing red "UNTESTED" warning; Phase 7 will add its
    own cooldown timer on top of this, deliberately not part of this
    phase.
  - "Apply Theme" gets its own collapsible "Customize the theme's
    parameters" checklist (the 9 non-root categories — THEME_CATEGORIES),
    reusing the exact same category icons as the Save wizard via a newly
    shared category_swatch_pixbuf() (previously a private method on
    SavePresetWizard; extracted so the two dialogs can't visually drift
    apart). apply_preset() gained the matching selected_categories
    parameter — an unchecked category is left completely untouched on
    the live system, not just hidden in the UI. A category that was
    skipped_on_purpose or not_applicable at save time starts unchecked
    here too, since applying it couldn't do anything anyway — but stays
    toggleable in case that status is ever wrong. Category selection is
    necessarily ignored for legacy (pre-Phase-1) presets, which have no
    per-category data to selectively apply from; a warning says so
    instead of silently applying everything regardless of the checklist.
  - New: stray GTK override detection (find_stray_gtk_overrides). Checks
    ~/.config/gtk-3.0/gtk.css, gtk-dark.css, and the GTK4 equivalents —
    files that sit outside dconf and outside any preset's own folder, so
    no preset switch can ever clear them, and they can make an applied
    theme look wrong for a reason that has nothing to do with the preset
    itself (hit once during dev testing). The Apply Theme section shows
    a red banner naming exactly which file(s) exist and offers to delete
    them, but only after an explicit confirmation — never automatic, and
    the banner rechecks itself right after every Apply Theme run.

Still on BETA-0.10 (Roadmap Phase 4 — Save Preset Wizard) adds:
  - Hitting "+ Save Current Desktop As New Preset" now opens a real modal
    flow (SavePresetWizard) instead of a single name prompt: a mandatory
    screenshot (reusing Phase 2's capture flow, now also hiding the main
    window during capture, not just the wizard), a mandatory name, an
    optional multi-line description, and a collapsible "Customize the
    theme's parameters" checklist covering all 12 categories from the
    design mockups — everything checked by default, since saving is
    local and risk-free. The old opt-in post-save screenshot prompt
    (_offer_screenshot) is gone; capture is part of the save flow itself
    now, not a follow-up.
  - save_preset() gained a real selected_categories parameter. Unchecking
    a category in the wizard means it's never captured at all — no dconf
    dump, no theme/addon file bundling, no LightDM/Plymouth/GRUB/profile-
    picture save call — and is marked "skipped_on_purpose" in
    meta.json's per-category status (a real status now, not just a
    reserved-but-unused enum value from Phase 3). bundle_assets() and
    bundle_addons() both gained an optional `kinds` filter to support
    this; defaulting to "every kind" keeps any other caller's behavior
    unchanged.
  - Name-collision check before overwriting an existing preset: the
    wizard stays open (screenshot/description intact) if you say no,
    instead of forcing you to redo the whole flow just to pick a
    different name.
  - Cursor/Icons/Panel/Profile Picture checklist rows now prefer a LIVE
    preview of what's actually currently active over a generic category
    icon, the same idea as Cinnamon Settings' own Themes page: Cursor and
    Icons pull straight from GDK/GTK's live theme state
    (Gdk.Cursor.get_image() — the same technique capture_cursor_overlay()
    already used for the screenshot's cursor overlay, so this isn't a new
    trick, just reused — and Gtk.IconTheme's own folder-icon lookup), no
    custom Xcursor-file parsing needed since our own process already
    tracks the active theme via XSETTINGS like any other GTK app. Panel
    resolves "cs-panel" — Cinnamon Settings' own icon for its Panel
    module page, which any icon theme meant to look native in Cinnamon
    Settings (including complete/retro packs like Mint-7 and Mint-XP)
    ships — falling back to the "start-here" family; no screenshot
    dependency at all (an earlier version of this cropped the screenshot
    directly, which needed one to exist first and only handled the
    single-panel case — replaced outright, not layered on top). Profile
    Picture reuses _accounts_get_icon_file(), the same AccountsService
    IconFile lookup save_profile_picture() itself already used, rather
    than assuming ~/.face specifically. All four fall back to the
    existing category-icon chain (custom art -> system icon -> gradient)
    on any failure, so a live preview can only improve a row, never make
    it worse.

BETA-0.9 (Roadmap Phase 3 — Data Model + Main List Rebuild) adds:
  - New meta.json fields: "name" (mirrors the folder name, kept in sync by
    rename_preset), "description" (empty until Phase 4's wizard exists to
    set it), "saved_at" (ISO timestamp, used for the new date sort), and
    "categories" — a computed status ("present" / "not_applicable" /
    "not_implemented" / "error", plus "skipped_on_purpose" reserved for
    Phase 4) for all 11 mockup categories, not just the 8 dconf-backed
    ones. Notably honest about "profile_picture": there's no
    AccountsService code anywhere in this app yet, so it's always
    reported "not_implemented" rather than faking a status for a feature
    that doesn't exist.
  - Presets saved before this version are normalized on read
    (_normalize_meta), not rewritten on disk — same non-destructive
    philosophy as the Phase 1 legacy-apply fallback. Older presets get a
    sensible computed "categories" status and an empty description
    instead of a missing field.
  - Main window rebuilt around a single Gtk.FlowBox that serves both grid
    and list view (file-manager style, per the roadmap's own framing):
    grid/list toggle, a thumbnail-size slider in grid mode, a search box
    (matches name + description), and a sort dropdown (Name / Date
    Saved).
  - Every preset now renders a real thumbnail — its saved screenshot if
    it has one, otherwise a deterministic gradient placeholder generated
    from a hash of its name (render_gradient_placeholder /
    load_thumbnail_pixbuf), so the list never shows a blank tile even
    for presets saved before Phase 2's screenshot capture existed.
  - Apply/Rename/Delete/System-Boot-Settings all gray out until a preset
    is actually selected, and selection now survives a list rebuild
    where it makes sense (rename, save, screenshot capture all reselect
    the affected preset afterward) instead of silently dropping back to
    nothing selected.
  - New dependency: python3-cairo (pycairo), for drawing the gradient
    placeholders. Not previously required.

BETA-0.8 fixes another real bundling gap, found the same way as BETA-0.6
(reading Cinnamon Settings' own source, not guessing): LightDM's
`background=` image is now bundled, not just the config file that
references it — same class of bug the desktop wallpaper handling already
solved, just not applied to LightDM until now. Presets saved before
BETA-0.8 need a re-save to pick this up; applying an old one falls back
to LightDM's default background since there's nothing bundled yet.

BETA-0.7 (Roadmap Phase 2 — Screenshot Capture Module) adds:
  - A standalone hide -> countdown -> capture -> keep/retake screenshot
    flow (ScreenshotCaptureFlow, near the top of the GTK UI section),
    with no external screenshot utility dependency — capture goes
    straight through GDK (Gdk.pixbuf_get_from_window on the root
    window), the same mechanism GTK itself already uses.
  - Hooked in as an opt-in follow-up step right after saving a new
    preset (CinnamonPresetsWindow._offer_screenshot), so it's actually
    exercised now rather than sitting unused until later phases. Phase
    4's Save wizard will make this mandatory and move it earlier in the
    flow; Phase 3's list will reuse the same module for a "retake
    thumbnail" action. Neither exists yet, so for now: decline the
    prompt and a preset saves exactly as it did before this version.
  - Every meta.json now has a "screenshot" key (default
    {"status": "none"}), so later phases have one consistent field to
    check regardless of which version a given preset was saved on.
  - Fixed the countdown badge itself showing up in the captured
    screenshot: destroy() on the overlay window only schedules the
    unmap, it doesn't wait for the compositor to actually redraw before
    the next line runs. Now flushes the display, drains pending GTK
    events, and waits ~150ms before the real capture.
  - Mouse cursor is now optional in the review dialog: a "Show mouse
    cursor in screenshot" checkbox, OFF by default (an arbitrary cursor
    position isn't really part of "the look" — same reasoning as every
    other opt-in default in this app). The base capture never has a
    cursor baked in either way; checking the box composites the current
    cursor theme's glyph on top, at the pointer's actual position, only
    at save time. No new dependency — Gdk.Cursor.get_image() already
    gives GDK's own cursor-theme pixbuf, no XFixes/ctypes needed.

BETA-0.6 fixes real, verified dconf key mistakes found in BETA-0.5's
allowlist — none of these ever errored (dconf write/read don't validate
against schemas), they just silently touched the wrong key or nothing at
all. Confirmed against Mint's own cs_themes.py source and a live
`dconf dump /org/cinnamon/` on Cinnamon 6.6.9:
  - The Cinnamon "Desktop" shell theme (panel/menu/calendar look — what
    Cinnamon Settings' Themes page calls "Desktop", bound to
    org.cinnamon.theme's `name` key, dconf path /org/cinnamon/theme/name)
    was NOT captured at all. BETA-0.5's comment claimed it "piggybacks on
    gtk-theme" — that's wrong; it's a fully separate key and a fully
    separate theme folder lookup. Now part of both the "style" dconf
    category and asset bundling (new "cinnamon" kind alongside gtk).
  - `panel-autohide` -> `panels-autohide` (the real key is plural).
  - `panel-resizable` -> `panels-resizable` (same mistake, same fix).
  - `panel-scale-text-icons` -> `panels-scale-text-icons`. The singular
    key does exist, but it's explicitly marked deprecated/inert in
    Cinnamon's own schema ("Retained to avoid applets who read the
    property from crashing Cinnamon") — BETA-0.5 was reading/writing a
    key nothing actually acts on.
  - Dropped `panel-launchers` from the allowlist — it's marked
    "Obsolete - unused" in the current schema, so keeping it did nothing
    but add dead weight.

BETA-0.5 (Roadmap Phase 1 — foundation) adds:
  - Replaced the whole-tree `dconf reset -f /org/cinnamon/` + `dconf load`
    with an explicit allowlist (CATEGORY_DCONF_KEYS / CATEGORY_DCONF_DIRS
    near the top of this file). Applying a preset used to silently roll
    back things that happen to live in the same dconf tree but have
    nothing to do with "theme" — favorite-apps, custom keybindings,
    panel-edit-mode — to whatever they were at save time. Now only
    specific, named keys/directories are ever touched, split across 8
    categories (Style, Cursor, Icons, Fonts, Sounds, Wallpaper, Panel
    Modifications, Widgets) that map 1:1 to the app's own UI categories.
  - Fault-isolated the whole apply flow to match the save side's existing
    _safe() pattern: one theme failing to copy, one addon's files being
    unreadable, or one dconf category failing to write no longer aborts
    the rest of Apply. Every step is independent and every failure is
    collected and reported, never silently swallowed and never fatal to
    the steps around it. apply_preset() now returns
    {"warnings": [...], "errors": [...], "applied_anything": bool}
    instead of a bare list, and only raises if literally nothing could be
    applied.
  - Presets saved before this version (single `cinnamon.dconf` whole-tree
    dump, no per-category data) still apply correctly via a legacy
    fallback path — but a clear note is surfaced recommending a re-save
    to move them onto the safer, scoped format.
  - Addon bundling (extensions/applets/desklets) is now explicitly mapped
    to its matching UI category (extensions -> Style, applets -> Panel
    Modifications, desklets -> Widgets) via ADDON_KIND_TO_CATEGORY, laying
    the groundwork for per-category Save/Export/Apply checklists.

BETA-0.4 adds:
  - Fixed the actual cause of Plymouth theme detection coming up empty:
    plymouth-set-default-theme lives in /usr/sbin, off a GUI session's
    PATH. Detection now tries `update-alternatives --query
    default.plymouth` first (usually on PATH, no root, and the real
    mechanism Mint/Ubuntu/Debian register the theme through), then falls
    back through several other methods. If every unprivileged method
    still comes up empty on a given system, the app offers a one-time,
    separately-authorized, read-only root check — not tied to the Apply
    flow, and no credentials are kept afterward.
  - Applying a Plymouth theme now sets it via `update-alternatives --set
    default.plymouth` (matching how `update-alternatives --config
    default.plymouth` would), falling back to plymouth-set-default-theme
    if update-alternatives isn't available, then always explicitly runs
    `update-initramfs -u` afterward.
  - Fixed a regression this introduced in an earlier BETA-0.4 pass: an
    unhandled error in the new panel-layout bundling (or in
    LightDM/Plymouth/GRUB) could abort save_preset() before meta.json
    was ever written, silently discarding the wallpaper/theme/addon data
    that had already been gathered in that same save. Every optional
    save step is now isolated so one failing can't cost the others.
  - New: per-app icon/launcher overrides (e.g. changing a single app's
    icon via the menu editor) are now bundled and restored. These are
    stored as override .desktop files under
    ~/.local/share/applications/, entirely outside dconf, so they were
    never covered before.
  - New: panel layout is now part of every preset. Panel/applet
    placement itself was already covered by the full dconf dump, but
    each applet's own settings (e.g. a Weather applet's chosen city) live
    outside dconf, as JSON files under ~/.cinnamon/configs/<uuid>/ —
    those are now bundled and restored too, automatically, no root
    needed.
  - GRUB Bootloader is marked untested in the System Boot Settings dialog
    (shown in red) — it hasn't been verified end-to-end yet, so double
    check the result yourself before rebooting with it.

BETA-0.3 added:
  - Bundling the actual files for any user-installed (non-stock) GTK/icon/
    cursor/sound theme and any user-installed extension/applet/desklet, so
    a preset still works after a fresh install or on another machine.
  - Optional, opt-in snapshotting and restoring of LightDM (login screen),
    Plymouth (boot splash), and GRUB (bootloader). These three are saved
    automatically (read-only, no root needed) whenever you save a preset,
    but applying each one is a separate, deliberate action that asks for
    admin rights on its own — authorizing one never grants access to the
    other two.

How the desktop part works: Cinnamon keeps almost all of its visual state
under one dconf tree, /org/cinnamon/, but that tree also holds unrelated
things (favorite-apps, keybindings). A preset now saves an explicit
allowlist of theme-related keys/directories, one snapshot per category
(see CATEGORY_DCONF_KEYS/CATEGORY_DCONF_DIRS), plus copies of anything
those keys merely reference by name (wallpaper image, custom themes,
custom extensions). Applying a preset writes/resets only those specific
keys — never the whole tree — restores any bundled theme/extension
files, then asks Cinnamon to reload itself. Every step is independent,
so a failure in one category or one file never blocks the rest.

Requires: python3-gi, gir1.2-gtk-3.0, python3-cairo, dconf-cli, policykit-1
(pkexec — present by default on Linux Mint Cinnamon). update-grub /
plymouth are part of Mint's default install.
"""

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango

import os
import re
import sys
import logging
from logging.handlers import RotatingFileHandler
import io
import json
import copy
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request
import webbrowser
import hashlib
import colorsys
import cairo
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

APP_NAME = "Cinnamon Presets"
VERSION = "BETA-0.18"

# TODO: fill these in once the accounts/repo are public.
GITHUB_REPO_URL = "https://github.com/SaadTerminal/Cinnamon-Presets.git"
PATREON_URL = ""
YOUTUBE_URL = ""

# Config/preset storage lives in its own folder, separate from wherever the
# app itself is installed. Uninstalling/reinstalling the app only touches
# the installed script + .desktop file + icon — it never touches this
# folder, so presets survive a reinstall or update.
CONFIG_DIR = Path.home() / ".config" / "cinnamon-presets"
PRESETS_DIR = CONFIG_DIR / "presets"
DCONF_PATH = "/org/cinnamon/"  # still used by the legacy (pre-allowlist) apply path, see apply_preset()

# Roadmap Phase 8: how often the silent startup check is allowed to run,
# not the manual "Check Now" button (which always forces an immediate
# check regardless of this). Stored on disk so the throttle survives
# between app launches, not just within one running session.
UPDATE_CHECK_STATE_FILE = CONFIG_DIR / "update_check_state.json"
UPDATE_CHECK_INTERVAL_SECONDS = 6 * 60 * 60  # roadmap: "every few hours"

# --- BETA-0.17 (Roadmap Phase 9 / Settings Tab addendum) ---------------
#
# Install paths, matching install.sh/uninstall.sh exactly (see their own
# BIN_DIR/APPS_DIR/ICON_DIR/HELPERS_DIR). Uninstall is a native Python
# reimplementation of uninstall.sh's deletions rather than a call into
# that script — see uninstall_app()'s docstring for why. Both need to be
# kept in sync on these same target paths if either ever changes.
INSTALLED_BIN_PATH = Path.home() / ".local" / "bin" / "cinnamon-presets"
INSTALLED_DESKTOP_FILE = Path.home() / ".local" / "share" / "applications" / "cinnamon-presets.desktop"
INSTALLED_ICON_PATH = (
    Path.home() / ".local" / "share" / "icons" / "hicolor" / "128x128" / "apps" / "cinnamon-presets.svg"
)
# uninstall.sh only ever rm -rf's the helpers/ subfolder here, missing the
# icons/categories/ subfolder install.sh also populates -- a small
# pre-existing gap in uninstall.sh. uninstall_app() below removes this
# whole directory instead (both subfolders at once), which is the more
# correct behavior; worth a matching one-line fix in uninstall.sh too.
INSTALLED_SHARE_DIR = Path.home() / ".local" / "share" / "cinnamon-presets"

# General tab: persisted UI defaults (view mode, thumbnail size, sort
# order). Deliberately its own small file, not folded into any preset's
# meta.json or a bigger config blob — App settings vs. saved-look data
# are different things with different lifecycles (Erase All Data wipes
# both together only because they happen to share CONFIG_DIR, not
# because this file is treated specially).
APP_SETTINGS_FILE = CONFIG_DIR / "settings.json"
DEFAULT_APP_SETTINGS = {
    "default_view_mode": "grid",
    "default_thumb_size": 160,
    "default_sort_mode": "name",
}

# Diagnostics tab: rotating log file, deliberately under its own logs/
# subfolder — separate from presets/ so exporting/backing up a look never
# bundles log noise, and so Erase All Data's effect on logs is just a
# consequence of sharing CONFIG_DIR, not a special case to reason about.
LOG_DIR = CONFIG_DIR / "logs"
LOG_FILE = LOG_DIR / "cinnamon-presets.log"

# Storage tab: low-space warning threshold. Hybrid (percentage capped by
# a flat ceiling) rather than either alone -- a flat number is
# unreasonable on a small drive, a pure percentage is misleading on a
# huge one (90% used on 1TB still leaves 100GB free). Two named
# constants, easy to retune later.
LOW_SPACE_PERCENT = 0.10
LOW_SPACE_CAP_BYTES = 30 * 1024 ** 3

# --- Phase 1: explicit dconf allowlist ---------------------------------
#
# BETA-0.4 and earlier did `dconf reset -f /org/cinnamon/` + `dconf load`
# on the ENTIRE tree. That's not actually safe: /org/cinnamon/ also holds
# things that have nothing to do with a "theme" — favorite-apps, custom
# keybindings, panel-edit-mode, etc. — so applying a preset saved weeks
# ago would silently roll those back to whatever they were at save time,
# not just change the look.
#
# Below is an explicit allowlist instead: only these specific keys/dirs
# are ever read, reset, or written. Two shapes:
#   - CATEGORY_DCONF_DIRS: whole directories that are unambiguously one
#     category and nothing else (background, sound), so a scoped
#     dump/reset/load on just that directory is safe.
#   - CATEGORY_DCONF_KEYS: individual keys, used wherever the directory
#     they live in mixes categories together (desktop/interface/ has
#     gtk-theme, icon-theme, cursor-theme, cursor-size, and font keys all
#     in one place) or is a single top-level /org/cinnamon/ key
#     (enabled-applets, enabled-desklets, enabled-extensions, panel-*).
#     Applying these is a per-key `dconf write`/`dconf reset` — surgical,
#     never a directory-wide reset — so nothing outside this exact list
#     is ever touched.
#
# NOTE FOR WHOEVER TESTS THIS NEXT: these key names are standard Cinnamon
# GSettings paths from public documentation/source, not verified against
# a live `dconf dump /org/cinnamon/` on an actual Mint machine. Run that
# dump and diff it against the lists below before relying on this for
# anything you can't afford to lose — Cinnamon version differences
# (5.x vs 6.x) could shift a key name slightly. Deliberately NOT
# included, even though they live in /org/cinnamon/: favorite-apps,
# custom keybindings, panel-edit-mode (a transient UI mode, not a saved
# look), and next-applet-id (bookkeeping — overwriting it backwards
# could collide with an applet instance added since the preset was
# saved; the exact instance IDs already travel inside enabled-applets
# itself, which IS in the allowlist).

CATEGORY_DCONF_DIRS = {
    "wallpaper": ["/org/cinnamon/desktop/background/"],
    # BETA-0.8 fix: "sounds" was pointed at only desktop/sound/ (which
    # really just holds the event-sounds master toggle + volume-sound-*).
    # The actual per-event file mappings (login-file, logout-file,
    # switch-file, etc.) live in a completely separate schema,
    # org.cinnamon.sounds -> /org/cinnamon/sounds/. Confirmed by reading
    # Cinnamon Settings' own cs_sound.py rather than guessing again.
    "sounds": ["/org/cinnamon/sounds/", "/org/cinnamon/desktop/sound/"],
}

CATEGORY_DCONF_KEYS = {
    # BETA-0.6: the Cinnamon shell theme (panel/menu/calendar — labeled
    # "Desktop" in Cinnamon Settings' Themes page) IS a separate key,
    # confirmed against Mint's own cs_themes.py: Gio.Settings.new
    # ("org.cinnamon.theme") -> key "name". A theme package can (and
    # often does) supply both a gtk-3.0/ folder and a cinnamon/ folder
    # under the same theme name, which is presumably how the earlier
    # "piggybacks on gtk-theme" assumption crept in — but they're
    # independently selectable and independently stored.
    "style": [
        "/org/cinnamon/desktop/interface/gtk-theme",
        "/org/cinnamon/theme/name",
        "/org/cinnamon/desktop/wm/preferences/theme",
        "/org/cinnamon/enabled-extensions",
    ],
    "cursor": [
        "/org/cinnamon/desktop/interface/cursor-theme",
        "/org/cinnamon/desktop/interface/cursor-size",
    ],
    "icons": [
        "/org/cinnamon/desktop/interface/icon-theme",
    ],
    "fonts": [
        "/org/cinnamon/desktop/interface/font-name",
        "/org/cinnamon/desktop/interface/document-font-name",
        "/org/cinnamon/desktop/interface/monospace-font-name",
        "/org/cinnamon/desktop/wm/preferences/titlebar-font",
    ],
    # No "sounds" entry here on purpose: the actual sound theme key
    # (theme-name) lives inside /org/cinnamon/desktop/sound/, which
    # CATEGORY_DCONF_DIRS["sounds"] already dumps/loads wholesale — a
    # separate KEYS entry pointing at desktop/interface/sound-theme was
    # here before, but that key doesn't exist in the real schema (fixed
    # BETA-0.8, see bundle_assets()/INTERFACE_KEYS fix in the same
    # commit for the other half of this bug).
    "panel": [
        "/org/cinnamon/enabled-applets",
        "/org/cinnamon/panels-enabled",
        "/org/cinnamon/panels-height",
        "/org/cinnamon/panels-autohide",         # was "panel-autohide" (wrong, no-op)
        "/org/cinnamon/panels-resizable",        # was "panel-resizable" (wrong, no-op)
        "/org/cinnamon/panels-scale-text-icons", # was "panel-scale-text-icons" (real key
                                                  # exists but is deprecated/inert — see
                                                  # BETA-0.6 changelog note above)
        "/org/cinnamon/panel-zone-icon-sizes",
        "/org/cinnamon/panel-zone-text-sizes",
        "/org/cinnamon/panel-zone-symbolic-icon-sizes",
        # panel-launchers dropped: marked "Obsolete - unused" in Cinnamon's
        # own schema, so it was never doing anything.
    ],
    "widgets": [
        "/org/cinnamon/enabled-desklets",
    ],
}

# All 8 dconf-backed categories (the other 3 from the design mockups —
# Profile Picture, Lock Screen, Boot Animation, GRUB — aren't dconf at
# all: Profile Picture is AccountsService, the other two are the
# existing LightDM/Plymouth/GRUB root-gated flow).
DCONF_CATEGORIES = ["style", "cursor", "icons", "fonts", "sounds", "wallpaper", "panel", "widgets"]

CATEGORY_LABELS = {
    "style": "Style", "cursor": "Cursor", "icons": "Icons", "fonts": "Fonts",
    "sounds": "Sounds", "wallpaper": "Wallpaper", "panel": "Panel Modifications",
    "widgets": "Widgets",
}

# Phase 1 item 3: which of the three addon buckets maps to which visual
# category — matches the roadmap 1:1 (extensions -> Style,
# applets -> Panel Modifications, desklets -> Widgets). bundle_addons()
# already keys its result by these three kinds; this mapping is what
# later phases (per-category apply/export checklists) will key off of.
ADDON_KIND_TO_CATEGORY = {
    "extensions": "style",
    "applets": "panel",
    "desklets": "widgets",
}

# ---------------------------------------------------------------------------
# Phase 3: per-category status tracking
#
# The 8 DCONF_CATEGORIES above are the dconf-backed subset. The full 11-item
# checklist from the design mockups also includes 3 non-dconf categories
# already implemented under other names (lightdm/plymouth/grub) plus one
# that ISN'T implemented at all yet (profile_picture — no AccountsService
# code exists anywhere in this file). CATEGORY_ORDER is every category the
# UI will ever show, in the mockup's own order; CATEGORY_UI_LABELS is the
# matching display name for each.
# ---------------------------------------------------------------------------

CATEGORY_ORDER = [
    "style", "cursor", "icons", "fonts", "sounds", "wallpaper",
    "profile_picture", "panel", "widgets", "lightdm", "plymouth", "grub",
]

CATEGORY_UI_LABELS = {
    "style": "Style", "cursor": "Cursor", "icons": "Icons", "fonts": "Fonts",
    "sounds": "Sounds", "wallpaper": "Wallpaper", "profile_picture": "Profile Picture",
    "panel": "Panel Modifications", "widgets": "Widgets",
    "lightdm": "Lock Screen", "plymouth": "Boot Animation", "grub": "GRUB Bootloader",
}

# Phase 5: the 9 categories apply_preset() actually handles without root —
# everything except the 3 boot-level items, which each get their own
# separately-authorized section/pkexec call in ApplyPresetDialog. This is
# CATEGORY_ORDER with lightdm/plymouth/grub excluded, kept as an explicit
# list (rather than filtering CATEGORY_ORDER at every use site) so it's
# one obvious place to look if that split ever needs to change.
THEME_CATEGORIES = [c for c in CATEGORY_ORDER if c not in ("lightdm", "plymouth", "grub")]

# Phase 4: the checklist body text under each category name, reused
# verbatim across Save/Export/Apply per the roadmap's "same visual
# language everywhere" design goal. Adapted from the design mockups, with
# two deliberate corrections against what's actually implemented: the
# mockup's "Panel Modifications" description mentions desklets, but
# desklets are their own category (Widgets, via ADDON_KIND_TO_CATEGORY) —
# repeating them under Panel too would misdescribe what unchecking either
# box actually does.
CATEGORY_DESCRIPTIONS = {
    "style": "The core theme design, color scheme and extensions.",
    "cursor": "The mouse cursor.",
    "icons": "The icon pack and modified individual app icons.",
    "fonts": "The fonts used in the system.",
    "sounds": "The system sound effects.",
    "wallpaper": "The background wallpaper.",
    "profile_picture": "The picture profile of the user.",
    "panel": "The panel layout, applets, and panel extensions.",
    "widgets": "Independent desklets shown on the desktop.",
    "lightdm": "Your LightDM login (and lock) screen appearance.",
    "plymouth": "The Plymouth boot animation.",
    "grub": "Your GRUB bootloader configuration and theme.",
}

# Status values a category can have. "skipped_on_purpose" is produced by
# Phase 4's Save wizard checklist: unchecking a category makes
# save_preset() skip capturing it entirely and mark it this way, rather
# than it looking indistinguishable from "error" or silently absent.
# "not_implemented" is specifically for profile_picture before it existed
# — kept in the enum for older presets saved against that version.
CATEGORY_STATUSES = ("present", "skipped_on_purpose", "not_applicable", "not_implemented", "error")


def _dconf_category_status(meta, category):
    """A dconf category's _dump_category() result always has one "keys"
    entry per allowlisted key (even if the value is None/unset) and one
    "dirs" entry per allowlisted directory — UNLESS the whole dump call
    threw and _safe() fell back to the empty {"keys": {}, "dirs": {}}
    default, OR the category was deliberately left out of a Phase 4 save
    (marked with "skipped_on_purpose" instead of ever calling
    _dump_category at all). So an entirely empty dict with no skip marker
    is the tell for "the save step itself failed", not "nothing was set"
    (a key that's merely unset still shows up in the dict, just with a
    None value)."""
    entry = (meta.get("dconf") or {}).get(category) or {}
    if entry.get("skipped_on_purpose"):
        return "skipped_on_purpose"
    if not entry.get("keys") and not entry.get("dirs"):
        return "error"
    return "present"


def compute_category_statuses(meta):
    """Derive a status for all 11 UI categories from whatever's already in
    meta.json. Called once at save time (and stored, so a preset's
    displayed status doesn't silently change if the allowlist itself
    changes later) and again on load for any preset saved before this
    field existed, so older presets still get a sensible status instead of
    a missing one."""
    statuses = {}

    for cat in ("style", "cursor", "icons", "fonts", "sounds", "panel", "widgets"):
        statuses[cat] = _dconf_category_status(meta, cat)

    wp_status = (meta.get("wallpaper") or {}).get("status")
    statuses["wallpaper"] = {
        "saved": "present",
        "not_a_local_file": "present",  # still captured via the dconf key, just not re-hosted
        "not_found": "not_applicable",
        "skipped_on_purpose": "skipped_on_purpose",
    }.get(wp_status, "error")

    pp_status = (meta.get("profile_picture") or {}).get("status")
    statuses["profile_picture"] = {
        "saved": "present",
        "not_found": "not_applicable",
        "skipped_on_purpose": "skipped_on_purpose",
    }.get(pp_status, "error" if pp_status else "not_implemented")

    lightdm_status = (meta.get("lightdm") or {}).get("status")
    statuses["lightdm"] = {
        "saved": "present",
        "not_found": "not_applicable",
        "skipped_on_purpose": "skipped_on_purpose",
    }.get(lightdm_status, "error")

    plymouth_status = (meta.get("plymouth") or {}).get("status")
    statuses["plymouth"] = {
        "bundled": "present",
        "system_only": "present",
        "not_found": "not_applicable",
        "skipped_on_purpose": "skipped_on_purpose",
    }.get(plymouth_status, "error")

    grub_status = (meta.get("grub") or {}).get("status")
    statuses["grub"] = {
        "saved": "present",
        "not_found": "not_applicable",
        "skipped_on_purpose": "skipped_on_purpose",
    }.get(grub_status, "error")

    return statuses


def _normalize_meta(name, meta):
    """Fill in defaults for fields that didn't exist in older meta.json
    versions, without rewriting the file on disk — a read-time
    normalization, same philosophy as apply_preset()'s legacy-format
    fallback: old presets keep working, they just don't retroactively
    gain data that was never captured."""
    meta = dict(meta or {})
    meta.setdefault("name", name)
    meta.setdefault("description", "")
    meta.setdefault("saved_at", None)
    meta.setdefault("screenshot", {"status": "none"})
    if "categories" not in meta:
        meta["categories"] = compute_category_statuses(meta)
    return meta

# BETA-0.8: "sound" used to be in here too, on the assumption Cinnamon
# picks one active "sound theme" the same way it picks one gtk-theme/
# icon-theme/cursor-theme. That assumption was wrong on two separate
# guesses in a row -- Cinnamon doesn't have a single sound theme concept
# at all. Confirmed via cs_sound.py: it's ~12 independent per-event
# key->filepath mappings (login-file, logout-file, switch-file, ...)
# under schema org.cinnamon.sounds, plus one more (volume-sound-file)
# under org.cinnamon.desktop.sound. No "pick the active theme folder"
# step applies here, so it doesn't belong in this dict or in
# bundle_assets()/restore_assets() at all -- see _bundle_sound_files_in_dump
# / _restore_sound_files_in_dump below for the real mechanism, which
# mirrors how wallpaper already bundles+rewrites a single file path,
# just run once per event key instead of once.
INTERFACE_KEYS = {
    "gtk": "/org/cinnamon/desktop/interface/gtk-theme",
    "cinnamon": "/org/cinnamon/theme/name",  # BETA-0.6: the actual shell theme, see above
    "icon": "/org/cinnamon/desktop/interface/icon-theme",
    "cursor": "/org/cinnamon/desktop/interface/cursor-theme",
}

ADDON_KINDS = {
    "extensions": "/org/cinnamon/enabled-extensions",
    "applets": "/org/cinnamon/enabled-applets",
    "desklets": "/org/cinnamon/enabled-desklets",
}

# Phase 4: which UI category owns each bundle_assets() kind — mirrors
# ADDON_KIND_TO_CATEGORY below, used the same way: the Save wizard's
# per-category checklist filters bundle_assets()'s kinds through this so
# unchecking "Icons" also skips bundling the icon theme's files, not just
# the icon-theme dconf key.
ASSET_KIND_TO_CATEGORY = {
    "gtk": "style",
    "cinnamon": "style",
    "icon": "icons",
    "cursor": "cursor",
}

LIGHTDM_CONF = Path("/etc/lightdm/slick-greeter.conf")
GRUB_DEFAULT = Path("/etc/default/grub")
# Matches the backup naming convention apply-grub.sh already used from
# BETA-0.3 onward (cp -a "$DEST" "$DEST.cinnamon-presets-backup" before
# every overwrite) -- Phase 7 builds a Restore action on top of a backup
# file that already existed, not a new one. apply-lightdm.sh has used the
# identical convention since the same phase.
GRUB_BACKUP_PATH = Path("/etc/default/grub.cinnamon-presets-backup")
LIGHTDM_BACKUP_PATH = Path("/etc/lightdm/slick-greeter.conf.cinnamon-presets-backup")

# Plymouth has no single config file to snapshot the way GRUB/LightDM
# do -- its "current state" is just which theme is active. BETA-0.17
# resolves this without touching apply-plymouth.sh at all: right before
# an Apply Boot Animation actually changes the theme,
# _record_plymouth_previous_theme() reads whatever theme is currently
# active (a plain unprivileged read, same call save_plymouth() already
# uses) and stashes it here, so Restore has something to undo back to.
PLYMOUTH_PREVIOUS_STATE_FILE = CONFIG_DIR / "plymouth_previous_theme.json"

# Per-instance applet settings (e.g. a Weather applet's chosen city) are
# NOT part of the /org/cinnamon/ dconf tree — Cinnamon stores those as
# JSON files here instead, one folder per applet uuid.
APPLET_CONFIG_DIR = Path.home() / ".cinnamon" / "configs"


# ---------------------------------------------------------------------------
# Core logic (no GTK here — kept separate so it can be tested/reused on its
# own, e.g. from a CLI, without needing a display).
# ---------------------------------------------------------------------------

def ensure_dirs():
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)


# --- BETA-0.17: logging (Roadmap Addendum: Diagnostics) --------------------
#
# Nothing like this existed before -- failures only ever showed up in a
# one-time dialog and then vanished, a real gap given how much of this app
# is pkexec/root system changes. Logs actions and results, not full file
# contents (e.g. "applied LightDM config" plus its stdout/stderr, never
# the actual contents of slick-greeter.conf) -- useful for troubleshooting
# without becoming an accidental dump of configuration details.

logger = logging.getLogger("cinnamon-presets")
logger.setLevel(logging.INFO)
logger.propagate = False


def setup_logging():
    """Call once, early in main(). Safe to call more than once (guards
    against double-adding the handler). Never raises -- logging is a
    diagnostic aid, not something that should ever stop the app from
    starting."""
    if logger.handlers:
        return
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(str(LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=3)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)

        def _log_uncaught(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return
            logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
            sys.__excepthook__(exc_type, exc_value, exc_tb)

        sys.excepthook = _log_uncaught
    except OSError:
        pass


def get_diagnostic_info():
    """Roadmap Addendum: 'Copy Diagnostic Info' one-click. Version plus
    the tail of the current log file -- cheap now that logging exists,
    meant to lower the friction of filing a good bug report."""
    lines = [f"{APP_NAME} {VERSION}"]
    try:
        if LOG_FILE.is_file():
            tail = LOG_FILE.read_text(errors="replace").splitlines()[-60:]
            lines.append("")
            lines.append("--- last 60 log lines ---")
            lines.extend(tail)
        else:
            lines.append("(no log file yet)")
    except OSError as e:
        lines.append(f"(couldn't read log file: {e})")
    return "\n".join(lines)


# --- BETA-0.17: General tab — persisted UI defaults -------------------------

def load_app_settings():
    if APP_SETTINGS_FILE.is_file():
        try:
            data = json.loads(APP_SETTINGS_FILE.read_text())
            merged = dict(DEFAULT_APP_SETTINGS)
            merged.update({k: v for k, v in data.items() if k in DEFAULT_APP_SETTINGS})
            return merged
        except (OSError, json.JSONDecodeError):
            pass
    return dict(DEFAULT_APP_SETTINGS)


def save_app_settings(settings):
    ensure_dirs()
    try:
        APP_SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    except OSError as e:
        logger.warning(f"Couldn't save app settings: {e}")


# --- BETA-0.17: Storage tab — disk usage -----------------------------------

def _dir_size_bytes(path):
    """Simple recursive size sum -- matches what a file manager shows,
    not du-style block-accurate, needs no subprocess call."""
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def _find_mount_point(path):
    path = str(Path(path).resolve())
    best = "/"
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and path.startswith(parts[1]) and len(parts[1]) > len(best):
                    best = parts[1]
    except OSError:
        pass
    return best


def get_storage_info():
    """Apparent disk usage of CONFIG_DIR (everything this app has ever
    written under its own folder — presets, settings, logs, update-check
    state), plus which disk it's actually on and how full that disk is."""
    base = CONFIG_DIR if CONFIG_DIR.is_dir() else Path.home()
    app_bytes = _dir_size_bytes(CONFIG_DIR) if CONFIG_DIR.is_dir() else 0
    total, used, free = shutil.disk_usage(base)
    return {
        "app_bytes": app_bytes,
        "total": total,
        "used": used,
        "free": free,
        "other_used": max(0, used - app_bytes),
        "mount_point": _find_mount_point(base),
    }


def is_low_space(free_bytes, total_bytes):
    threshold = min(total_bytes * LOW_SPACE_PERCENT, LOW_SPACE_CAP_BYTES)
    return free_bytes < threshold


def format_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


# --- BETA-0.17: Storage tab — Danger Zone -----------------------------------

def erase_all_data():
    """Deletes ~/.config/cinnamon-presets ONLY -- presets, settings,
    logs, update-check state. The app itself stays installed. Never
    touches home-directory theme folders (~/.themes, ~/.icons, etc.) an
    Apply already copied files into, and never touches root-owned system
    paths -- neither this nor uninstall requests root, and a look
    someone installed via a preset should survive wiping the app's own
    data, the same way it survives an Uninstall."""
    if CONFIG_DIR.is_dir():
        shutil.rmtree(CONFIG_DIR)


def uninstall_app(purge=False):
    """Native Python reimplementation of uninstall.sh's own deletions,
    not a call into that script — uninstall.sh lives wherever the repo
    was cloned into, not copied anywhere persistent the way the helper
    scripts are, so it may well be gone by the time someone clicks an
    in-app Uninstall button. Must be kept in sync with uninstall.sh on
    the same target paths if either changes.

    purge=False (default): removes the installed binary, .desktop entry,
    icon, and this app's own ~/.local/share/cinnamon-presets folder.
    Never touches ~/.config/cinnamon-presets.

    purge=True: also removes ~/.config/cinnamon-presets (presets,
    settings, logs — everything Erase All Data would).

    Never touches home-directory theme folders or root-owned system
    paths, under either option — same scope as erase_all_data(). Safe to
    call while running: deleting a running script/binary on Linux is
    fine, the process keeps running off its inode until it exits."""
    removed = []
    errors = []

    for path in (INSTALLED_BIN_PATH, INSTALLED_DESKTOP_FILE, INSTALLED_ICON_PATH):
        try:
            if path.exists() or path.is_symlink():
                path.unlink()
                removed.append(str(path))
        except OSError as e:
            errors.append(f"{path}: {e}")

    try:
        if INSTALLED_SHARE_DIR.is_dir():
            shutil.rmtree(INSTALLED_SHARE_DIR)
            removed.append(str(INSTALLED_SHARE_DIR))
    except OSError as e:
        errors.append(f"{INSTALLED_SHARE_DIR}: {e}")

    if purge and CONFIG_DIR.is_dir():
        try:
            shutil.rmtree(CONFIG_DIR)
            removed.append(str(CONFIG_DIR))
        except OSError as e:
            errors.append(f"{CONFIG_DIR}: {e}")

    return {"removed": removed, "errors": errors}


def run(cmd, input_data=None):
    return subprocess.run(cmd, input=input_data, capture_output=True, text=True)


def sanitize_name(name):
    """Keep preset folder names filesystem-safe."""
    name = name.strip()
    name = re.sub(r"[^\w\-. ]", "", name)
    return name


def _helpers_dir():
    """Find the folder holding apply-*.sh helper scripts. Prefers a
    'helpers' folder next to this script (running from a git checkout
    without installing), falls back to the installed location."""
    dev_dir = Path(__file__).resolve().parent / "helpers"
    if dev_dir.is_dir():
        return dev_dir
    return Path.home() / ".local" / "share" / "cinnamon-presets" / "helpers"


def get_wallpaper_uri():
    result = run(["dconf", "read", "/org/cinnamon/desktop/background/picture-uri"])
    val = result.stdout.strip()
    if val.startswith("'") and val.endswith("'"):
        val = val[1:-1]
    return val


def wallpaper_path_from_uri(uri):
    if not uri:
        return None
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        return unquote(parsed.path)
    return None


def _rewrite_wallpaper_uri(dump_text, new_uri):
    """Point the picture-uri key in a saved dump at the preset's own
    bundled copy of the wallpaper, instead of the original file path."""
    lines = dump_text.splitlines()
    out = []
    in_bg_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_bg_section = stripped == "[desktop/background]"
            out.append(line)
            continue
        if in_bg_section and line.startswith("picture-uri="):
            out.append(f"picture-uri='{new_uri}'")
            continue
        out.append(line)
    return "\n".join(out) + "\n"


def _rewrite_wallpaper_in_dir_dump(dump_text, new_uri):
    """Same idea as _rewrite_wallpaper_uri, but for a dump taken directly
    of /org/cinnamon/desktop/background/ (the new per-category format) —
    picture-uri there sits under the root '[/]' section instead of a
    '[desktop/background]' subsection, since that directory itself is
    the dump's base path."""
    lines = dump_text.splitlines()
    out = []
    in_root_section = True
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_root_section = stripped == "[/]"
            out.append(line)
            continue
        if in_root_section and line.startswith("picture-uri="):
            out.append(f"picture-uri='{new_uri}'")
            continue
        out.append(line)
    return "\n".join(out) + "\n"


# --- Phase 1: per-category dconf save/apply ---------------------------
#
# Replaces the old single whole-tree dump/reset/load. Each category is
# read, reset, and written independently — see the CATEGORY_DCONF_*
# allowlist comment above for why. Deliberately no `reset -f` on any
# multi-purpose directory: directory dumps only happen for wallpaper/
# sounds, which are single-purpose directories; everything else goes
# through individual `dconf write`/`dconf reset` calls on named keys.

def _dump_category(category):
    """Read this category's allowlisted keys/dirs off the live system.
    Never raises on an individual key/dir read failure — that key is
    just recorded as unset, since a missing value shouldn't cost the
    rest of the category."""
    entry = {"keys": {}, "dirs": {}}
    for key in CATEGORY_DCONF_KEYS.get(category, []):
        try:
            val = run(["dconf", "read", key]).stdout.strip()
        except Exception:
            val = ""
        entry["keys"][key] = val or None  # None = unset / at default
    for d in CATEGORY_DCONF_DIRS.get(category, []):
        try:
            result = run(["dconf", "dump", d])
            entry["dirs"][d] = result.stdout if result.returncode == 0 else None
        except Exception:
            entry["dirs"][d] = None
    return entry


def _apply_category(category, entry):
    """Apply one category's saved keys/dirs. Best-effort per key/dir: one
    failing (e.g. a malformed stored value) is recorded as an error
    string and everything else in the category still gets applied.
    Returns a list of error strings (empty if everything succeeded)."""
    errors = []
    for key, val in (entry or {}).get("keys", {}).items():
        try:
            if val:
                r = run(["dconf", "write", key, val])
                if r.returncode != 0:
                    errors.append(f"{key}: {r.stderr.strip() or 'write failed'}")
            else:
                # Wasn't set (at default) when saved — reset just this
                # one key back to default too, so switching presets is
                # still deterministic without touching anything else in
                # the directory it lives in.
                run(["dconf", "reset", key])
        except Exception as e:
            errors.append(f"{key}: {e}")

    for d, dump_text in (entry or {}).get("dirs", {}).items():
        try:
            reset_result = run(["dconf", "reset", "-f", d])
            if reset_result.returncode != 0:
                errors.append(f"{d}: reset failed — {reset_result.stderr.strip()}")
                continue
            if dump_text:
                load_result = run(["dconf", "load", d], input_data=dump_text)
                if load_result.returncode != 0:
                    errors.append(f"{d}: load failed — {load_result.stderr.strip()}")
        except Exception as e:
            errors.append(f"{d}: {e}")

    return errors


# --- Theme asset bundling (GTK / icon / cursor) -----------------------------
# (sound is handled separately below -- see the INTERFACE_KEYS comment for
# why it doesn't fit this "one active theme folder" model)

def _asset_search_dirs(kind, name):
    home = Path.home()
    if kind in ("gtk", "cinnamon"):
        # Same theme-package folders for both: a package that supplies a
        # Cinnamon shell theme puts it in <theme>/cinnamon/ right next to
        # <theme>/gtk-3.0/, under the same top-level theme name — whether
        # or not the two keys are actually set to the same name.
        return [home / ".themes" / name, home / ".local/share/themes" / name,
                Path("/usr/share/themes") / name]
    if kind in ("icon", "cursor"):
        return [home / ".icons" / name, home / ".local/share/icons" / name,
                Path("/usr/share/icons") / name]
    return []


def _is_dpkg_managed(path):
    """True if `path` is owned by an installed .deb package (dpkg -S) --
    meaning it's part of the base system or a package Mint's own repos
    can reinstall, safe to assume present on any Mint install without
    bundling it. False for anything dpkg doesn't recognize, which covers
    BOTH a theme dropped straight into /usr/share/themes/ by hand (sudo
    cp, no package involved -- genuinely at risk of vanishing, just as
    much as one under ~/.themes) and anything under a user's own home
    directory (dpkg never owns files there anyway).

    This exists because directory location alone ("/usr/share/... must
    be stock") was the previous heuristic, and it was wrong: a custom,
    manually-root-installed theme living under /usr/share/themes/ looked
    identical to an actual Mint-shipped one, so it silently never got
    bundled -- the preset would apply the theme's *name* on another
    machine (or after a reinstall) with no files behind it. dpkg -S
    actually answers the real question ("was this installed by the
    package manager") instead of guessing from where it happens to sit.

    Debian/Ubuntu/Mint only, which is fine here -- dpkg not being on
    PATH (or the query failing for any reason) is treated as "can't
    tell," which defaults to False -- i.e. bundle it anyway. Over-
    bundling a theme that turns out to be package-managed costs a bit of
    disk space in the preset; under-bundling one that isn't silently
    breaks the look. The safe direction to default toward is obvious."""
    try:
        result = subprocess.run(
            ["dpkg", "-S", str(path)],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def find_asset_dir(kind, name):
    for d in _asset_search_dirs(kind, name):
        if d.is_dir():
            loc = "system" if _is_dpkg_managed(d) else "user"
            return d, loc
    return None, "missing"


def _clear_dir(path):
    """Remove a directory (and everything in it) if it exists. Called
    right before repopulating a bundle destination, so a fresh save
    reflects only what's currently active instead of accumulating every
    theme/addon/GRUB-theme that was ever active across this preset's
    save history — dirs_exist_ok=True on its own only ever merges in,
    never removes what's no longer relevant. Safe to call on a path that
    doesn't exist yet."""
    if path.is_dir():
        shutil.rmtree(path)


def bundle_assets(preset_dir, kinds=None):
    """Save the *name* of each theme (already captured by the dconf dump
    too) plus, for any user-installed custom theme, the actual files.
    kinds optionally restricts which of INTERFACE_KEYS to process --
    Phase 4's Save wizard checklist uses this so unchecking a category
    (e.g. Icons) skips bundling its files too, not just its dconf key.
    Defaults to every kind, matching pre-Phase-4 behavior for any other
    caller."""
    result = {}
    selected_kinds = INTERFACE_KEYS.keys() if kinds is None else kinds
    for kind in selected_kinds:
        key = INTERFACE_KEYS[kind]
        raw = run(["dconf", "read", key]).stdout.strip()
        name = raw.strip("'") if raw else ""
        if not name:
            continue
        src, loc = find_asset_dir(kind, name)
        entry = {"name": name, "status": loc}
        if loc == "user":
            kind_dir = preset_dir / "assets" / kind
            _clear_dir(kind_dir)
            dest = kind_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dest, dirs_exist_ok=True)
            entry["status"] = "bundled"
        result[kind] = entry
    return result


def restore_assets(preset_dir, assets_meta):
    dest_roots = {
        "gtk": Path.home() / ".themes",
        "cinnamon": Path.home() / ".themes",
        "icon": Path.home() / ".icons",
        "cursor": Path.home() / ".icons",
    }
    missing = []
    errors = []
    for kind, entry in (assets_meta or {}).items():
        name = entry.get("name")
        status = entry.get("status")
        if not name:
            continue
        if status == "bundled":
            src = preset_dir / "assets" / kind / name
            dest = dest_roots[kind] / name
            if src.is_dir():
                try:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                except Exception as e:
                    errors.append(f"{kind} theme '{name}': {e}")
        elif status == "missing":
            missing.append(f"{kind} theme '{name}'")
    return missing, errors


# --- Sound event files -------------------------------------------------------
#
# BETA-0.8: Cinnamon has no single "sound theme" -- it's ~12 independent
# per-event key->filepath mappings (org.cinnamon.sounds: login-file,
# logout-file, switch-file, map-file, close-file, minimize-file,
# maximize-file, unmaximize-file, tile-file, plug-file, unplug-file,
# notification-file) plus one more, volume-sound-file, under the separate
# org.cinnamon.desktop.sound schema. Each key is just an absolute path to
# an audio file, which can live under /usr/share/mint-artwork/sounds/
# (Cinnamon's own default location), /usr/share/sounds/ (Freedesktop/
# GNOME/ALSA stock resources Mint also ships), or anywhere in the user's
# own home directory. Three possible "stock" locations means trying to
# classify stock-vs-custom per file is fragile -- so instead this always
# bundles whatever file each key currently points to, no classification
# needed, since audio files are small (a few KB-few hundred KB each,
# ~12-13 of them). Mirrors how wallpaper is already handled: bundle the
# file, then on Apply rewrite the path to point at this preset's own
# restored copy -- which always lands in the user's own home directory,
# so this never needs root even for sounds that originally lived under
# /usr/share/ (reading a world-readable system file needs no special
# permission; only writing back to /usr/share/ would have).

_SOUND_FILE_KEY_RE = re.compile(r"^([\w-]+-file)='([^']*)'\s*$", re.MULTILINE)


def _bundle_sound_files_in_dump(preset_dir, dump_text, subdir):
    """Find every '<event>-file=...' line in a sound-schema dconf dump and
    copy the file it points to into the preset. subdir keeps the two
    sound schemas (org.cinnamon.sounds vs org.cinnamon.desktop.sound)
    from colliding on disk, since both can have a 'volume-sound-file'-
    shaped key name in principle. Returns a manifest dict describing what
    happened to each key -- the raw dump text itself is left untouched
    here (still pointing at the *original* machine's paths); the rewrite
    to the preset's own bundled copy happens separately, at Apply time,
    via _restore_sound_files_in_dump."""
    manifest = {}
    if not dump_text:
        return manifest
    for key, path in _SOUND_FILE_KEY_RE.findall(dump_text):
        if not path:
            continue
        src = Path(path)
        if not src.is_file():
            manifest[key] = {"original": path, "status": "missing"}
            continue
        dest_rel = f"assets/sounds/{subdir}/{key}/{src.name}"
        dest = preset_dir / dest_rel
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            manifest[key] = {"original": path, "bundled": dest_rel, "status": "bundled"}
        except Exception as e:
            manifest[key] = {"original": path, "status": "error", "error": str(e)}
    return manifest


def _restore_sound_files_in_dump(preset_dir, dump_text, subdir, manifest):
    """Inverse of the above: rewrite each '<event>-file=...' line to point
    at this preset's own bundled copy, restored into
    ~/.local/share/sounds/cinnamon-presets/<subdir>/<key>/<filename> --
    always user-space, regardless of where the file originally lived when
    it was saved."""
    if not dump_text:
        return dump_text
    dest_root = Path.home() / ".local/share/sounds/cinnamon-presets" / subdir

    def _replace(m):
        key, _old_path = m.group(1), m.group(2)
        entry = (manifest or {}).get(key)
        if not entry or entry.get("status") != "bundled":
            return m.group(0)
        src = preset_dir / entry["bundled"]
        if not src.is_file():
            return m.group(0)
        dest = dest_root / key / src.name
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        except Exception:
            return m.group(0)
        return f"{key}='{dest}'"

    return _SOUND_FILE_KEY_RE.sub(_replace, dump_text)


# --- Extension / applet / desklet bundling ----------------------------------

def _extract_uuid(entry):
    """Applet entries look like 'panel1:right:0:uuid@author:0'; extension
    and desklet entries are usually just 'uuid@author'. Pull the uuid out
    either way."""
    m = re.search(r"([\w.\-]+@[\w.\-]+)", entry)
    return m.group(1) if m else entry


def find_addon_dir(uuid, kind):
    user_dir = Path.home() / ".local/share/cinnamon" / kind / uuid
    sys_dir = Path("/usr/share/cinnamon") / kind / uuid
    if user_dir.is_dir():
        return user_dir, "user"
    if sys_dir.is_dir():
        return sys_dir, "system"
    return None, "missing"


def bundle_addons(preset_dir, kinds=None):
    result = {}
    selected_kinds = ADDON_KINDS.keys() if kinds is None else kinds
    for kind in selected_kinds:
        key = ADDON_KINDS[kind]
        result[kind] = {}
        # Clear once per kind, before the uuid loop below -- an addon
        # that was enabled in an earlier save but isn't anymore should
        # disappear from the bundle, not just accumulate forever.
        _clear_dir(preset_dir / "addons" / kind)
        raw = run(["dconf", "read", key]).stdout
        for entry in re.findall(r"'([^']*)'", raw):
            uuid = _extract_uuid(entry)
            if not uuid:
                continue
            src, loc = find_addon_dir(uuid, kind)
            if loc == "user":
                dest = preset_dir / "addons" / kind / uuid
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dest, dirs_exist_ok=True)
                result[kind][uuid] = "bundled"
            else:
                result[kind][uuid] = loc  # "system" or "missing"
    return result


def restore_addons(preset_dir, addons_meta):
    missing = []
    errors = []
    for kind, entries in (addons_meta or {}).items():
        for uuid, status in entries.items():
            if status == "bundled":
                src = preset_dir / "addons" / kind / uuid
                dest = Path.home() / ".local/share/cinnamon" / kind / uuid
                if src.is_dir():
                    try:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(src, dest, dirs_exist_ok=True)
                    except Exception as e:
                        singular = kind[:-1] if kind.endswith("s") else kind
                        errors.append(f"{singular} '{uuid}': {e}")
            elif status == "missing":
                singular = kind[:-1] if kind.endswith("s") else kind
                missing.append(f"{singular} '{uuid}'")
    return missing, errors


# --- LightDM / Plymouth / GRUB: save (read-only, no root needed) -----------

def _ini_get(text, section, key):
    """Small helper: pull `key=value` out of an ini-style file under
    [section]. Good enough for slick-greeter.conf's simple format."""
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped[1:-1].strip().lower() == section.lower()
            continue
        if in_section and "=" in stripped and not stripped.startswith("#"):
            k, _, v = stripped.partition("=")
            if k.strip().lower() == key.lower():
                return v.strip()
    return None


def save_lightdm(preset_dir):
    if not LIGHTDM_CONF.is_file():
        return {"status": "not_found"}

    dest_dir = preset_dir / "system" / "lightdm"
    dest_dir.mkdir(parents=True, exist_ok=True)
    text = LIGHTDM_CONF.read_text(errors="ignore")
    shutil.copy2(LIGHTDM_CONF, dest_dir / LIGHTDM_CONF.name)

    entry = {"status": "saved", "background_file": None}

    # slick-greeter's `background` key under [Greeter] can be a real
    # image path OR a plain color (e.g. "#dc8add") -- LightDM runs before
    # the user's own session exists, so if it's a path, that image has to
    # be bundled the same way the desktop wallpaper already is, or the
    # preset silently breaks the moment that file moves/is deleted.
    bg_value = _ini_get(text, "Greeter", "background")
    if bg_value and not bg_value.startswith("#") and "://" not in bg_value:
        bg_path = Path(bg_value)
        if bg_path.is_file():
            ext = bg_path.suffix or ".img"
            dest = dest_dir / f"background{ext}"
            try:
                shutil.copy2(bg_path, dest)
                entry["background_file"] = dest.name
            except (PermissionError, OSError) as e:
                entry["background_status"] = f"unreadable: {e}"
        else:
            # Referenced but already gone even at save time -- nothing to
            # bundle; surfaced in the UI so it's not a silent gap.
            entry["background_status"] = "missing"

    # slick-greeter's theme-name/icon-theme-name/cursor-theme-name are
    # its OWN separate theme selection for the login/lock screen --
    # commonly, but not always, the same as the desktop session's. Never
    # bundled before this: only `background` was ever inspected here.
    # LightDM runs as its own system user before any session exists, so
    # these have to live somewhere world-readable (never a regular
    # user's own ~/.themes) -- but a custom one manually installed under
    # /usr/share/themes/ or /usr/share/icons/ is exactly as much at risk
    # of vanishing as anything under ~/.themes, so it gets the same
    # bundle-if-not-package-managed treatment bundle_assets() already
    # gives the desktop session's own theme (see find_asset_dir /
    # _is_dpkg_managed).
    entry["assets"] = {}
    for key, kind in (
        ("theme-name", "gtk"),
        ("icon-theme-name", "icon"),
        ("cursor-theme-name", "cursor"),
    ):
        name = _ini_get(text, "Greeter", key)
        if not name:
            continue
        src, loc = find_asset_dir(kind, name)
        asset_entry = {"name": name, "status": loc}
        if loc == "user":
            asset_dest_dir = dest_dir / "assets" / kind
            _clear_dir(asset_dest_dir)
            dest = asset_dest_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copytree(src, dest, dirs_exist_ok=True)
                asset_entry["status"] = "bundled"
            except (PermissionError, OSError) as e:
                asset_entry["status"] = f"unreadable: {e}"
        entry["assets"][kind] = asset_entry

    return entry


def _plymouth_theme_from_alternatives(env=None):
    """update-alternatives is how Debian/Ubuntu/Mint actually register
    which Plymouth theme is active -- it's what
    `update-alternatives --config default.plymouth` edits. Querying it
    is read-only, needs no root, and (unlike plymouth-set-default-theme)
    the binary lives in /usr/bin, so it's reliably on a normal desktop
    session's PATH. This is the most reliable unprivileged detection
    method and is tried first."""
    try:
        result = subprocess.run(
            ["update-alternatives", "--query", "default.plymouth"],
            capture_output=True, text=True, env=env,
        )
    except (FileNotFoundError, PermissionError):
        return None
    for line in result.stdout.splitlines():
        if line.startswith("Value:"):
            value = line.split(":", 1)[1].strip()
            p = Path(value)
            name = p.parent.name if p.suffix == ".plymouth" else p.name
            if name:
                return name
    return None


def _plymouth_current_theme():
    """Find the name of the currently-active Plymouth theme, without
    needing root. Tries several methods in order of reliability, since
    which one works varies by system:

    1. `update-alternatives --query default.plymouth` (usually on PATH,
       no root needed, and how Mint/Ubuntu/Debian register the theme)
    2. `plymouth-set-default-theme` with no args, searching /usr/sbin
       explicitly since GUI sessions often don't have it on PATH
    3. Reading /etc/alternatives/default.plymouth or
       /etc/plymouth/plymouthd.conf directly

    Returns None if every unprivileged method comes up empty — the
    caller can then decide whether to offer a one-time admin-rights
    retry via save_plymouth_with_root().
    """
    theme = _plymouth_theme_from_alternatives()
    if theme:
        return theme

    search_path = os.environ.get("PATH", "") + os.pathsep + "/usr/sbin:/sbin:/usr/local/sbin"
    env = dict(os.environ, PATH=search_path)
    for cmd in ("plymouth-set-default-theme", "/usr/sbin/plymouth-set-default-theme",
                "/sbin/plymouth-set-default-theme"):
        try:
            result = subprocess.run([cmd], capture_output=True, text=True, env=env)
        except (FileNotFoundError, PermissionError):
            continue
        theme = result.stdout.strip()
        if theme:
            return theme

    # Fallback: /etc/alternatives/default.plymouth is the symlink both
    # tools above ultimately resolve on Debian/Ubuntu/Mint.
    link = Path("/etc/alternatives/default.plymouth")
    try:
        if link.is_symlink():
            target = Path(os.readlink(link))
            name = target.parent.name if target.suffix == ".plymouth" else target.name
            if name and name != "alternatives":
                return name
    except OSError:
        pass

    # Fallback: the theme can also be set directly in plymouthd.conf.
    conf = Path("/etc/plymouth/plymouthd.conf")
    if conf.is_file():
        m = re.search(r"^\s*Theme\s*=\s*(\S+)", conf.read_text(errors="ignore"), re.MULTILINE)
        if m:
            return m.group(1).strip()

    return None


def _bundle_plymouth_theme(preset_dir, theme):
    entry = {"theme": theme, "status": "system_only"}
    theme_dir = Path("/usr/share/plymouth/themes") / theme
    if theme_dir.is_dir():
        plymouth_dir = preset_dir / "system" / "plymouth"
        _clear_dir(plymouth_dir)
        dest = plymouth_dir / theme
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copytree(theme_dir, dest, dirs_exist_ok=True)
            entry["status"] = "bundled"
        except (PermissionError, OSError):
            pass
    return entry


def save_plymouth(preset_dir):
    theme = _plymouth_current_theme()
    if not theme:
        return {"status": "not_found", "theme": None}
    return _bundle_plymouth_theme(preset_dir, theme)


def save_plymouth_with_root(preset_dir):
    """Last-resort, opt-in fallback when every unprivileged detection
    method in _plymouth_current_theme() comes up empty. Runs one narrow,
    read-only pkexec helper that only reports the current theme name —
    it never writes anything — then bundles it exactly like save_plymouth()
    would have. This is its own separate authorization, only triggered
    when the user agrees to it, and grants nothing beyond this one call:
    no credentials are cached, so saving again later asks again."""
    helper = _helpers_dir() / "read-plymouth-theme.sh"
    result = run(["pkexec", "bash", str(helper)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Cancelled or failed.")
    theme = result.stdout.strip()
    if not theme:
        raise RuntimeError("No Plymouth theme reported.")
    return _bundle_plymouth_theme(preset_dir, theme)


def save_grub(preset_dir):
    entry = {"status": "not_found", "theme": None, "theme_status": None}
    if not GRUB_DEFAULT.is_file():
        return entry
    dest_dir = preset_dir / "system" / "grub"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GRUB_DEFAULT, dest_dir / "grub_default")
    entry["status"] = "saved"

    text = GRUB_DEFAULT.read_text(errors="ignore")
    m = re.search(r'^GRUB_THEME="?([^"\n]+)"?', text, re.MULTILINE)
    if m:
        theme_path = Path(m.group(1).strip())
        theme_dir = theme_path.parent if theme_path.name == "theme.txt" else theme_path
        theme_name = theme_dir.name
        entry["theme"] = theme_name
        if theme_dir.is_dir():
            theme_root = dest_dir / "theme"
            _clear_dir(theme_root)
            tdest = theme_root / theme_name
            tdest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copytree(theme_dir, tdest, dirs_exist_ok=True)
                entry["theme_status"] = "bundled"
            except (PermissionError, OSError):
                entry["theme_status"] = "system_only"
        else:
            entry["theme_status"] = "missing"
    return entry


# --- Profile Picture (AccountsService) --------------------------------------
#
# The account avatar shown at the LightDM login screen and in Cinnamon's own
# user menu isn't a dconf value -- it's managed by AccountsService, a system
# D-Bus service, referenced via each user's IconFile property. Unlike
# LightDM/Plymouth/GRUB, changing *your own* account's icon specifically
# does NOT need pkexec/root: accountsservice's own polkit rule
# (org.freedesktop.accounts.change-own-user-data) is auth_self by default,
# meaning a user is allowed to change their own icon with no elevation at
# all. Reading the current value needs nothing special either. Uses gdbus
# (present by default alongside glib on any Cinnamon system) rather than
# adding a python-dbus dependency, matching how the rest of this file shells
# out to dconf/pkexec/etc. instead of using their Python bindings.

def _accounts_user_path():
    return f"/org/freedesktop/Accounts/User{os.getuid()}"


def _accounts_get_icon_file():
    """Current account avatar path, or None if unset/unreadable."""
    result = run([
        "gdbus", "call", "--system",
        "--dest", "org.freedesktop.Accounts",
        "--object-path", _accounts_user_path(),
        "--method", "org.freedesktop.DBus.Properties.Get",
        "org.freedesktop.Accounts.User", "IconFile",
    ])
    if result.returncode != 0:
        return None
    m = re.search(r"'([^']*)'", result.stdout)
    return m.group(1) if m and m.group(1) else None


def save_profile_picture(preset_dir):
    icon_path = _accounts_get_icon_file()
    if not icon_path or not Path(icon_path).is_file():
        return {"status": "not_found"}
    src = Path(icon_path)
    dest_dir = preset_dir / "profile_picture"
    _clear_dir(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"avatar{src.suffix or '.png'}"
    try:
        shutil.copy2(src, dest)
    except (PermissionError, OSError) as e:
        return {"status": "error", "error": str(e)}
    return {"status": "saved", "file": dest.name}


def apply_profile_picture(preset_dir, meta):
    """No pkexec on purpose -- see the module comment above. Raises on
    failure like apply_lightdm/apply_plymouth/apply_grub do, so it slots
    into apply_preset()'s existing per-step try/except the same way."""
    entry = (meta or {}).get("profile_picture") or {}
    if entry.get("status") != "saved" or not entry.get("file"):
        raise FileNotFoundError("No saved profile picture in this preset.")
    src = preset_dir / "profile_picture" / entry["file"]
    if not src.is_file():
        raise FileNotFoundError("Bundled profile picture file is missing.")
    # ~/.face is the conventional handoff spot GNOME/Mint's own avatar
    # picker uses -- accountsservice (running as root) reads the path we
    # give it itself, so it just needs to be somewhere world-readable.
    dest = Path.home() / ".face"
    shutil.copy2(src, dest)
    result = run([
        "gdbus", "call", "--system",
        "--dest", "org.freedesktop.Accounts",
        "--object-path", _accounts_user_path(),
        "--method", "org.freedesktop.Accounts.User.SetIconFile",
        str(dest),
    ])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Failed to set profile picture.")


def _safe(fn, *args, default=None):
    """Run a best-effort save/bundle step and never let it take the rest
    of the preset save down with it. Before BETA-0.4, an unexpected error
    in any one step (e.g. a permissions quirk, or the new panel-layout
    bundling hitting an unreadable applet config folder) raised out of
    save_preset() entirely — since meta.json is only written at the very
    end, that silently discarded EVERYTHING already gathered in that
    save, including the wallpaper and theme/addon bundling that had
    already succeeded. Now each step's failure is recorded against just
    that step, and the rest of the preset still gets saved."""
    try:
        return fn(*args)
    except Exception as e:
        return default if default is not None else {"status": "error", "error": str(e)}


# --- Panel layout: applet placement + per-applet settings ------------------
#
# Applet/panel placement (which panel, zone, order) lives in the
# enabled-applets key and various panel-* keys, all under /org/cinnamon/ —
# so the full `dconf dump` already captures and restores that, no extra
# work needed. What it does NOT capture is each applet's own settings
# (e.g. a Weather applet's chosen city, a Menu applet's chosen icon):
# Cinnamon stores those separately as JSON files under
# ~/.cinnamon/configs/<uuid>/, outside dconf entirely. This bundles and
# restores those files so a restored panel doesn't just look right, it
# behaves right too.

def _enabled_applet_uuids():
    raw = run(["dconf", "read", ADDON_KINDS["applets"]]).stdout
    uuids = []
    for entry in re.findall(r"'([^']*)'", raw):
        uuid = _extract_uuid(entry)
        if uuid and uuid not in uuids:
            uuids.append(uuid)
    return uuids


def save_panel_layout(preset_dir):
    saved = []
    dest_root = preset_dir / "panel" / "configs"
    # Same class of bug as bundle_assets/bundle_addons/_bundle_plymouth_theme/
    # save_grub -- clear once, before the loop, so an applet that was
    # enabled in an earlier save but isn't anymore doesn't leave its old
    # config folder behind forever.
    _clear_dir(dest_root)
    for uuid in _enabled_applet_uuids():
        src = APPLET_CONFIG_DIR / uuid
        if src.is_dir():
            dest = dest_root / uuid
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dest, dirs_exist_ok=True)
            saved.append(uuid)
    return {"status": "saved" if saved else "none", "applets": saved}


def restore_panel_layout(preset_dir, panel_meta):
    errors = []
    src_root = preset_dir / "panel" / "configs"
    for uuid in (panel_meta or {}).get("applets", []):
        src = src_root / uuid
        if src.is_dir():
            dest = APPLET_CONFIG_DIR / uuid
            try:
                # Same reasoning as the save side: clear this applet's
                # live config folder before restoring into it, so a key
                # this preset's version doesn't have (e.g. dropped by an
                # older applet schema) doesn't linger merged in alongside
                # the restored ones.
                _clear_dir(dest)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dest, dirs_exist_ok=True)
            except Exception as e:
                errors.append(f"applet settings for '{uuid}': {e}")
    return errors


# --- Per-app icon/launcher overrides ----------------------------------------
#
# Changing an individual app's icon (right-click a menu entry → "Edit
# properties", or the menu editor) doesn't touch dconf at all — Cinnamon
# writes a modified copy of that app's .desktop file to
# ~/.local/share/applications/, overriding the system one in
# /usr/share/applications/ without changing it. Since the dconf dump never
# covered this, a restored preset kept whatever icon happened to be active
# at restore time (usually the plain system default) instead of the one
# that was actually saved. This bundles every override .desktop file plus
# any custom icon image file they point to by absolute path.

DESKTOP_OVERRIDES_DIR = Path.home() / ".local" / "share" / "applications"


def save_desktop_overrides(preset_dir):
    if not DESKTOP_OVERRIDES_DIR.is_dir():
        return {"status": "none", "files": [], "icons": []}
    files = []
    icons = []
    dest_dir = preset_dir / "desktop-overrides"
    icon_dest_dir = preset_dir / "desktop-overrides-icons"
    for entry in sorted(DESKTOP_OVERRIDES_DIR.glob("*.desktop")):
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry, dest_dir / entry.name)
        files.append(entry.name)

        text = entry.read_text(errors="ignore")
        m = re.search(r"^Icon=(/.+)$", text, re.MULTILINE)
        if m:
            icon_path = Path(m.group(1).strip())
            if icon_path.is_file():
                bundle_name = f"{len(icons):04d}_{icon_path.name}"
                icon_dest_dir.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(icon_path, icon_dest_dir / bundle_name)
                    icons.append({"bundle_name": bundle_name, "original_path": str(icon_path)})
                except OSError:
                    pass
    return {"status": "saved" if files else "none", "files": files, "icons": icons}


def restore_desktop_overrides(preset_dir, meta_entry):
    meta_entry = meta_entry or {}
    files = meta_entry.get("files") or []
    icons = meta_entry.get("icons") or []
    errors = []
    if not files and not icons:
        return errors

    src_dir = preset_dir / "desktop-overrides"
    if files:
        DESKTOP_OVERRIDES_DIR.mkdir(parents=True, exist_ok=True)
        for name in files:
            src = src_dir / name
            if src.is_file():
                try:
                    shutil.copy2(src, DESKTOP_OVERRIDES_DIR / name)
                except Exception as e:
                    errors.append(f"icon override '{name}': {e}")

    icon_src_dir = preset_dir / "desktop-overrides-icons"
    home = Path.home()
    for icon in icons:
        src = icon_src_dir / icon.get("bundle_name", "")
        orig = icon.get("original_path")
        if not (src.is_file() and orig):
            continue
        orig_path = Path(orig)
        # Only ever restore inside the user's own home directory — this
        # runs with no root, and a system-owned icon path shouldn't need
        # restoring anyway (it wasn't the user's custom file).
        try:
            orig_path.relative_to(home)
        except ValueError:
            continue
        try:
            orig_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, orig_path)
        except Exception as e:
            errors.append(f"custom icon image '{orig_path.name}': {e}")

    # Best-effort cache refresh so the menu picks up the change without
    # needing a logout. Not required, so failures are silently ignored.
    try:
        subprocess.run(
            ["update-desktop-database", str(DESKTOP_OVERRIDES_DIR)],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        pass

    return errors


# --- LightDM / Plymouth / GRUB: apply (root, one scoped pkexec call each) --

def _run_pkexec_helper(cmd, action_label):
    """Runs one pkexec helper script and logs its stdout/stderr either
    way — exactly the detail needed to answer "why did GRUB apply fail"
    after the fact, which used to only ever show up once in a dialog and
    then vanish. Every pkexec call site in this app goes through this
    now instead of duplicating the same run-then-check pattern."""
    result = run(cmd)
    logger.info(
        f"{action_label}: rc={result.returncode} "
        f"stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}"
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Cancelled or failed.")
    return result.stdout.strip()


def apply_lightdm(preset_dir, meta):
    src = preset_dir / "system" / "lightdm" / LIGHTDM_CONF.name
    if not src.is_file():
        raise FileNotFoundError("No saved LightDM greeter config in this preset.")

    lightdm_meta = (meta or {}).get("lightdm") or {}
    bg_file = lightdm_meta.get("background_file")
    bg_arg = ""
    if bg_file:
        bg_src = preset_dir / "system" / "lightdm" / bg_file
        if bg_src.is_file():
            bg_arg = str(bg_src)

    # Same idea as the background image: a bundled (i.e. was custom, not
    # package-managed) greeter theme/icon-theme/cursor-theme needs
    # reinstalling to /usr/share/{themes,icons}/<name>/ or the greeter
    # just silently falls back to a default the moment the original
    # system-wide copy is gone. Passed positionally, in a fixed order,
    # rather than as JSON — keeps the helper script plain bash with no
    # parsing dependency. Empty string means "not bundled" (either
    # nothing set, or find_asset_dir judged it package-managed already).
    asset_args = []
    lightdm_assets = lightdm_meta.get("assets") or {}
    for kind in ("gtk", "icon", "cursor"):
        asset = lightdm_assets.get(kind) or {}
        name = asset.get("name", "") or ""
        bundle_dir = ""
        if asset.get("status") == "bundled" and name:
            candidate = preset_dir / "system" / "lightdm" / "assets" / kind / name
            if candidate.is_dir():
                bundle_dir = str(candidate)
        asset_args.extend([name, bundle_dir])

    helper = _helpers_dir() / "apply-lightdm.sh"
    return _run_pkexec_helper(
        ["pkexec", "bash", str(helper), str(src), bg_arg, preset_dir.name, *asset_args],
        f"apply lightdm ({preset_dir.name})",
    )


def apply_plymouth(preset_dir, meta):
    plymouth_meta = (meta or {}).get("plymouth") or {}
    theme = plymouth_meta.get("theme")
    if not theme:
        raise FileNotFoundError("No saved Plymouth theme in this preset.")
    bundle_dir = preset_dir / "system" / "plymouth" / theme
    bundle_arg = str(bundle_dir) if bundle_dir.is_dir() else ""
    helper = _helpers_dir() / "apply-plymouth.sh"
    return _run_pkexec_helper(
        ["pkexec", "bash", str(helper), theme, bundle_arg],
        f"apply plymouth ({preset_dir.name}, theme={theme})",
    )


def apply_grub(preset_dir, meta):
    grub_meta = (meta or {}).get("grub") or {}
    if grub_meta.get("status") != "saved":
        raise FileNotFoundError("No saved GRUB config in this preset.")
    src = preset_dir / "system" / "grub" / "grub_default"
    theme_name = grub_meta.get("theme") or ""
    theme_bundle = preset_dir / "system" / "grub" / "theme" / theme_name if theme_name else None
    theme_arg = str(theme_bundle) if theme_bundle and theme_bundle.is_dir() else ""
    helper = _helpers_dir() / "apply-grub.sh"
    return _run_pkexec_helper(
        ["pkexec", "bash", str(helper), str(src), theme_arg, theme_name],
        f"apply grub ({preset_dir.name})",
    )


def grub_backup_exists():
    """No root needed -- /etc is world-readable, only writing to it needs
    pkexec. Used to decide whether ApplyPresetDialog's GRUB row shows a
    Restore button at all."""
    return GRUB_BACKUP_PATH.is_file()


def restore_grub_backup():
    """Roadmap Phase 7: restores /etc/default/grub from the backup
    apply-grub.sh already creates before every overwrite, then reruns
    update-grub. Not tied to any one preset -- this undoes whatever this
    app's own most recent GRUB apply did, regardless of which preset
    that was, the same way a person would expect an "undo" to work
    rather than needing to remember which preset they applied last."""
    if not grub_backup_exists():
        raise FileNotFoundError("No GRUB backup found — nothing to restore.")
    helper = _helpers_dir() / "restore-grub.sh"
    return _run_pkexec_helper(["pkexec", "bash", str(helper)], "restore grub backup")


def lightdm_backup_exists():
    """Same idea as grub_backup_exists() -- no root needed just to check
    whether the file is there."""
    return LIGHTDM_BACKUP_PATH.is_file()


def restore_lightdm_backup():
    """BETA-0.17 (Roadmap Addendum: Backups, b-lite). Restores
    /etc/lightdm/slick-greeter.conf from the backup apply-lightdm.sh
    already creates before every overwrite -- same "undo the app's own
    last change, not tied to one preset" model as restore_grub_backup()."""
    if not lightdm_backup_exists():
        raise FileNotFoundError("No LightDM backup found — nothing to restore.")
    helper = _helpers_dir() / "restore-lightdm.sh"
    return _run_pkexec_helper(["pkexec", "bash", str(helper)], "restore lightdm backup")


def _record_plymouth_previous_theme():
    """Best-effort snapshot of the currently-active Plymouth theme, taken
    right before an Apply Boot Animation actually changes it, so Restore
    has something to undo back to. Silent on failure -- this is a
    nice-to-have Restore convenience, never a reason for the apply itself
    to fail. Called from ApplyPresetDialog right before apply_plymouth()."""
    theme = _plymouth_current_theme()
    if not theme:
        return
    try:
        ensure_dirs()
        PLYMOUTH_PREVIOUS_STATE_FILE.write_text(json.dumps({
            "theme": theme,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }))
    except OSError:
        pass


def plymouth_backup_exists():
    return PLYMOUTH_PREVIOUS_STATE_FILE.is_file()


def restore_plymouth_backup():
    """BETA-0.17 (Roadmap Addendum: Backups, b-lite — this is the "open
    technical question" the addendum flagged). Plymouth has no single
    config file to snapshot, so "restore" means re-applying whichever
    theme _record_plymouth_previous_theme() last saw active, through the
    exact same apply-plymouth.sh path a normal apply uses (with no
    bundle dir, since the theme in question is necessarily already
    installed -- it was the live theme a moment ago). This needed no
    changes to apply-plymouth.sh at all."""
    if not plymouth_backup_exists():
        raise FileNotFoundError("No previous Plymouth theme recorded — nothing to restore.")
    data = json.loads(PLYMOUTH_PREVIOUS_STATE_FILE.read_text())
    theme = data.get("theme")
    if not theme:
        raise FileNotFoundError("No previous Plymouth theme recorded — nothing to restore.")
    helper = _helpers_dir() / "apply-plymouth.sh"
    return _run_pkexec_helper(
        ["pkexec", "bash", str(helper), theme, ""],
        f"restore plymouth backup (theme={theme})",
    )


# --- Preset list / save / apply / delete / rename ---------------------------

def list_presets():
    ensure_dirs()
    return sorted(p.name for p in PRESETS_DIR.iterdir() if p.is_dir())


def load_meta(name):
    meta_file = PRESETS_DIR / name / "meta.json"
    if meta_file.exists():
        return _normalize_meta(name, json.loads(meta_file.read_text()))
    return _normalize_meta(name, {})


# --- BETA-0.17: preset migration -------------------------------------------
#
# _normalize_meta() above already backfills missing fields on every read,
# but it's read-time-only and never persists — a preset saved a few
# versions back keeps paying that normalization cost forever, and more
# importantly, a *legacy* preset (the pre-Phase-1 whole-tree cinnamon.dconf
# format) has no per-category data for _normalize_meta to backfill from at
# all, so it's permanently stuck on apply_preset()'s less-safe legacy
# whole-tree fallback path — even though nothing about that desktop look
# actually needs re-capturing from a live system to fix that.
#
# migrate_preset() closes that gap: it reparses an old whole-tree dconf
# dump directly into the same per-category shape _dump_category() would
# have produced, using the exact same CATEGORY_DCONF_KEYS/DIRS allowlist,
# and writes the result back to meta.json once. No live desktop state is
# read or required — this works even if the current desktop looks nothing
# like the preset being migrated.

SCHEMA_VERSION = 2


def _parse_legacy_dconf_dump(dump_text):
    """Parses a legacy whole-tree `dconf dump /org/cinnamon/` INI-style
    dump into the same {"keys": {...}, "dirs": {...}} per-category shape
    _dump_category() produces from a live system. Pure text parsing, no
    dconf calls — this is what lets a legacy preset be upgraded without
    needing the live desktop to currently match it."""
    sections = {}
    current = None
    for raw_line in dump_text.splitlines():
        line = raw_line.rstrip("\n")
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections.setdefault(current, {})
            continue
        if current is not None and "=" in line:
            key, _, value = line.partition("=")
            sections[current][key.strip()] = value.strip()

    def read_key(full_key):
        rel = full_key[len(DCONF_PATH):] if full_key.startswith(DCONF_PATH) else full_key
        sect, sep, keyname = rel.rpartition("/")
        sect = sect if sep else "/"
        return sections.get(sect, {}).get(keyname)

    dconf = {}
    for cat in DCONF_CATEGORIES:
        entry = {"keys": {}, "dirs": {}}
        for key in CATEGORY_DCONF_KEYS.get(cat, []):
            entry["keys"][key] = read_key(key)
        for d in CATEGORY_DCONF_DIRS.get(cat, []):
            rel_dir = d[len(DCONF_PATH):].strip("/") if d.startswith(DCONF_PATH) else d.strip("/")
            lines = ["[/]"]
            for sect_name, sect_keys in sections.items():
                if sect_name == rel_dir:
                    for k, v in sect_keys.items():
                        lines.append(f"{k}={v}")
                elif sect_name.startswith(rel_dir + "/"):
                    lines.append(f"[{sect_name[len(rel_dir) + 1:]}]")
                    for k, v in sect_keys.items():
                        lines.append(f"{k}={v}")
            entry["dirs"][d] = ("\n".join(lines) + "\n") if len(lines) > 1 else None
        dconf[cat] = entry
    return dconf


def migrate_preset(name):
    """Upgrades one preset's meta.json in place, once. Idempotent — a
    preset already at SCHEMA_VERSION is a no-op. Returns True if anything
    was actually rewritten, False if it was already current."""
    preset_dir = PRESETS_DIR / name
    meta_file = preset_dir / "meta.json"
    raw = json.loads(meta_file.read_text()) if meta_file.exists() else {}

    if raw.get("schema_version") == SCHEMA_VERSION:
        return False

    meta = _normalize_meta(name, raw)

    legacy_dump = preset_dir / "cinnamon.dconf"
    if not meta.get("dconf") and legacy_dump.is_file():
        try:
            meta["dconf"] = _parse_legacy_dconf_dump(legacy_dump.read_text())
        except Exception as e:
            # A parse hiccup shouldn't block the rest of the migration —
            # worst case, this preset just keeps using the legacy
            # whole-tree apply path for dconf specifically, same as
            # before this ever ran.
            meta.setdefault("migration_warnings", []).append(f"dconf reparse failed: {e}")

    meta["categories"] = compute_category_statuses(meta)
    meta["schema_version"] = SCHEMA_VERSION
    meta_file.write_text(json.dumps(meta, indent=2))
    return True


def migrate_all_presets():
    """Runs migrate_preset() over every saved preset. Called once at
    startup — cheap (near-instant no-op) for anything already current, so
    nobody has to think about this; see Settings > Diagnostics for a
    manual re-run. Returns {name: True/False/"error: ..."}."""
    results = {}
    for name in list_presets():
        try:
            results[name] = migrate_preset(name)
        except Exception as e:
            results[name] = f"error: {e}"
    return results


def save_preset(name, description="", selected_categories=None):
    """selected_categories: optional {category_key: bool}, from Phase 4's
    Save wizard checklist. Any category not present in the dict defaults
    to True, so every pre-Phase-4 caller (and the dict-less default of
    None) keeps saving everything, same as before this parameter existed.
    An explicitly unchecked category is never captured at all -- no dconf
    dump, no asset/addon bundling, no boot-item save call -- and is
    marked "skipped_on_purpose" (see compute_category_statuses) instead
    of coming out looking like a failed capture."""
    name = sanitize_name(name)
    if not name:
        raise ValueError("Preset name can't be empty.")
    ensure_dirs()
    preset_dir = PRESETS_DIR / name
    preset_dir.mkdir(parents=True, exist_ok=True)

    def _sel(cat):
        return True if selected_categories is None else selected_categories.get(cat, True)

    meta = {}
    meta["name"] = name
    meta["description"] = description or ""
    meta["saved_at"] = datetime.now(timezone.utc).isoformat()

    # Phase 1: per-category dconf snapshot, not a whole-tree dump. See the
    # CATEGORY_DCONF_* allowlist comment near the top of the file for why.
    # Each category is isolated with _safe() same as everything else here.
    # Phase 4: a category the wizard checklist left unchecked never gets
    # its _dump_category() call made at all -- skipped outright, not
    # captured-then-discarded.
    meta["dconf"] = {}
    for cat in DCONF_CATEGORIES:
        if _sel(cat):
            meta["dconf"][cat] = _safe(_dump_category, cat, default={"keys": {}, "dirs": {}})
        else:
            meta["dconf"][cat] = {"keys": {}, "dirs": {}, "skipped_on_purpose": True}

    # BETA-0.8: bundle the actual audio files each sound-event key points
    # to (see the "Sound event files" section above for why this can't
    # just be part of bundle_assets() like GTK/icon/cursor). Uses the
    # dump text just captured above, so it has to run right after it.
    meta["sound_files"] = {}
    if _sel("sounds"):
        sounds_dirs = meta.get("dconf", {}).get("sounds", {}).get("dirs", {})
        for subdir, dconf_dir in (
            ("cinnamon", "/org/cinnamon/sounds/"),
            ("desktop", "/org/cinnamon/desktop/sound/"),
        ):
            meta["sound_files"][subdir] = _safe(
                _bundle_sound_files_in_dump, preset_dir, sounds_dirs.get(dconf_dir), subdir,
                default={},
            )

    # Wallpaper. Wrapped like everything below it: if this ever throws,
    # it must not cost us the assets/addons/panel/boot-item bundling that
    # runs after it, since meta.json is only written once, at the end.
    if _sel("wallpaper"):
        meta["wallpaper"] = {"status": "not_found"}
        try:
            uri = get_wallpaper_uri()
            meta["wallpaper_original_uri"] = uri
            wp_path = wallpaper_path_from_uri(uri)
            if wp_path and os.path.isfile(wp_path):
                ext = Path(wp_path).suffix or ".img"
                dest = preset_dir / f"wallpaper{ext}"
                shutil.copy2(wp_path, dest)
                meta["wallpaper_file"] = dest.name
                meta["wallpaper"] = {"status": "saved"}
            elif uri:
                # picture-uri was set to something we can't treat as a
                # plain local file (e.g. a slideshow .xml, or a non-
                # file:// scheme). The URI itself is still in the
                # "wallpaper" dconf category either way, so Apply won't
                # lose it -- this just means no separate copy of the
                # image got bundled into the preset.
                meta["wallpaper"] = {"status": "not_a_local_file"}
        except Exception as e:
            meta["wallpaper"] = {"status": "error", "error": str(e)}
    else:
        meta["wallpaper"] = {"status": "skipped_on_purpose"}

    # Everything below is best-effort and read-only on the local system —
    # no root needed for any of it, even the LightDM/Plymouth/GRUB parts.
    # Each step is isolated with _safe() so one failing (e.g. a locked
    # applet config file) can't cost us the others. asset_kinds/addon_kinds
    # restrict bundle_assets()/bundle_addons() to only the kinds whose
    # owning category is actually checked.
    asset_kinds = [k for k, cat in ASSET_KIND_TO_CATEGORY.items() if _sel(cat)]
    addon_kinds = [k for k, cat in ADDON_KIND_TO_CATEGORY.items() if _sel(cat)]
    meta["assets"] = _safe(bundle_assets, preset_dir, asset_kinds, default={})
    meta["addons"] = _safe(bundle_addons, preset_dir, addon_kinds, default={})

    meta["panel"] = (
        _safe(save_panel_layout, preset_dir, default={"status": "error", "applets": []})
        if _sel("panel") else {"status": "skipped_on_purpose", "applets": []}
    )
    meta["desktop_overrides"] = (
        _safe(save_desktop_overrides, preset_dir, default={"status": "error", "files": [], "icons": []})
        if _sel("icons") else {"status": "skipped_on_purpose", "files": [], "icons": []}
    )
    meta["lightdm"] = _safe(save_lightdm, preset_dir) if _sel("lightdm") else {"status": "skipped_on_purpose"}
    meta["plymouth"] = _safe(save_plymouth, preset_dir) if _sel("plymouth") else {"status": "skipped_on_purpose"}
    meta["grub"] = _safe(save_grub, preset_dir) if _sel("grub") else {"status": "skipped_on_purpose"}
    meta["profile_picture"] = (
        _safe(save_profile_picture, preset_dir, default={"status": "error"})
        if _sel("profile_picture") else {"status": "skipped_on_purpose"}
    )

    # Phase 2: no screenshot is captured as part of save_preset() itself —
    # capture is its own separate, hide/countdown/review flow that only
    # makes sense once the app window (and Gtk.main loop) already exists.
    # Phase 4 made it mandatory and moved it into the Save wizard itself
    # (SavePresetWizard), which calls save_screenshot() + patches this key
    # in right after save_preset() returns. This just guarantees every
    # meta.json has a "screenshot" field to check even if that follow-up
    # step somehow never ran.
    meta.setdefault("screenshot", {"status": "none"})

    # Phase 3: computed last, once every other field above has settled,
    # so it reflects what actually happened in THIS save rather than being
    # guessed from a partial meta dict.
    meta["categories"] = compute_category_statuses(meta)

    # BETA-0.17: stamp the schema version a fresh save is already written
    # in, so migrate_preset() has nothing to do the very first time it
    # ever sees this preset.
    meta["schema_version"] = SCHEMA_VERSION

    (preset_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    logger.info(f"saved preset '{name}': categories={meta.get('categories')}")
    return preset_dir, meta


def update_preset_meta(name, key, value):
    """Patch a single top-level key in an already-saved preset's
    meta.json, e.g. after a follow-up root-assisted Plymouth read."""
    preset_dir = PRESETS_DIR / name
    meta = load_meta(name)
    meta[key] = value
    # Some keys (plymouth, wallpaper, dconf, lightdm, grub) feed directly
    # into compute_category_statuses() — recompute so "categories" never
    # goes stale after a post-save patch like the Plymouth root retry.
    if key != "categories":
        meta["categories"] = compute_category_statuses(meta)
    (preset_dir / "meta.json").write_text(json.dumps(meta, indent=2))


# --- Phase 5: stray GTK override detection ----------------------------
#
# ~/.config/gtk-3.0/gtk.css (and gtk-dark.css), plus the GTK4 equivalents
# under ~/.config/gtk-4.0/, are a user-level override GTK applies on TOP
# of whatever theme is active — completely outside dconf and outside any
# ~/.themes/<name>/ folder, so no preset switch can ever touch it, let
# alone clear it. If one exists, an applied theme can look "wrong" (a
# stale color forced in, a widget style stuck) in a way that has nothing
# to do with the preset that was just applied — hit once already during
# dev testing. Detection only; deletion always needs its own explicit
# confirmation from whoever's using the app (see
# ApplyThemeSection._on_delete_gtk_override) — this never auto-removes
# anything.

GTK_OVERRIDE_FILES = [
    Path.home() / ".config/gtk-3.0/gtk.css",
    Path.home() / ".config/gtk-3.0/gtk-dark.css",
    Path.home() / ".config/gtk-4.0/gtk.css",
    Path.home() / ".config/gtk-4.0/gtk-dark.css",
]


def find_stray_gtk_overrides():
    """Returns the subset of GTK_OVERRIDE_FILES that actually exist right
    now. Pure filesystem check, no side effects."""
    return [p for p in GTK_OVERRIDE_FILES if p.is_file()]


def apply_preset(name, selected_categories=None):
    """Applies everything that doesn't need root: dconf settings, wallpaper,
    bundled themes, bundled extensions/applets/desklets, panel layout, and
    per-app icon overrides. LightDM/Plymouth/GRUB are NOT touched here —
    those are separate, deliberate, per-item actions (see apply_lightdm/
    apply_plymouth/apply_grub) since each needs its own admin authorization.

    Phase 1 fault isolation: every step below is independent. One theme
    failing to copy, one addon's files being unreadable, or one dconf
    category failing to write does NOT stop the others — each failure is
    recorded and everything else still gets applied. dconf itself is only
    ever touched through the explicit per-category allowlist (see
    CATEGORY_DCONF_KEYS/CATEGORY_DCONF_DIRS), never a whole-tree reset, so
    a partial apply can never wipe something the preset never touched in
    the first place.

    Phase 5: selected_categories is an optional {category_key: bool} from
    ApplyPresetDialog's own "Customize the theme's parameters" checklist —
    same shape and same "missing key defaults to True" rule as
    save_preset()'s. An unchecked category is left completely untouched on
    the live system: no dconf write/reset for it, no asset/addon restore
    for the kinds that belong to it. This only applies to presets saved in
    the Phase 1+ per-category format — a legacy (whole-tree) preset has no
    per-category dconf data to selectively apply from, so category
    selection is ignored for it and a warning says so instead of silently
    doing nothing.

    Returns a dict:
      {"warnings": [...],   # referenced by the preset but not found anywhere
                             # on this system — will simply be missing
       "errors": [...],     # found, but failed to actually apply/copy/write
       "applied_anything": bool}
    Raises only if NOTHING could be applied at all (e.g. no saved data, or
    every single step failed) — a partial success never raises.
    """
    preset_dir = PRESETS_DIR / name
    meta = load_meta(name)
    legacy_dconf_file = preset_dir / "cinnamon.dconf"
    has_new_format = bool(meta.get("dconf"))

    if not has_new_format and not legacy_dconf_file.exists():
        raise FileNotFoundError(f"No saved data found for preset '{name}'.")

    def _sel(cat):
        return True if selected_categories is None else selected_categories.get(cat, True)

    warnings = []
    errors = []
    applied_anything = False

    # --- dconf ---
    if has_new_format:
        for category, entry in meta["dconf"].items():
            if not _sel(category):
                continue
            entry = dict(entry or {})
            # Point the wallpaper category's background dump at this
            # preset's own bundled copy of the image, if it has one.
            if category == "wallpaper":
                wp_file = meta.get("wallpaper_file")
                if wp_file and (preset_dir / wp_file).exists():
                    new_uri = (preset_dir / wp_file).resolve().as_uri()
                    dirs = dict(entry.get("dirs", {}))
                    for d, text in dirs.items():
                        if text:
                            dirs[d] = _rewrite_wallpaper_in_dir_dump(text, new_uri)
                    entry["dirs"] = dirs
            # BETA-0.8: point each sound-event key at this preset's own
            # bundled copy of that event's audio file, same idea as the
            # wallpaper rewrite just above -- see "Sound event files"
            # section for why sound needs its own per-key handling
            # instead of the single-active-theme pattern.
            if category == "sounds":
                sound_files_meta = meta.get("sound_files", {})
                dirs = dict(entry.get("dirs", {}))
                for subdir, dconf_dir in (
                    ("cinnamon", "/org/cinnamon/sounds/"),
                    ("desktop", "/org/cinnamon/desktop/sound/"),
                ):
                    text = dirs.get(dconf_dir)
                    if text:
                        dirs[dconf_dir] = _restore_sound_files_in_dump(
                            preset_dir, text, subdir, sound_files_meta.get(subdir, {})
                        )
                entry["dirs"] = dirs
            try:
                cat_errors = _apply_category(category, entry)
            except Exception as e:
                cat_errors = [str(e)]
            if cat_errors:
                label = CATEGORY_LABELS.get(category, category)
                errors.extend(f"{label}: {msg}" for msg in cat_errors)
            else:
                applied_anything = True
    else:
        # Legacy preset (saved before Phase 1) — no per-category data was
        # ever captured for it, so fall back to the old whole-tree
        # reset+load. Still wrapped so a failure here is reported instead
        # of raising past everything below it.
        try:
            dump_text = legacy_dconf_file.read_text()
            wp_file = meta.get("wallpaper_file")
            if wp_file and (preset_dir / wp_file).exists():
                new_uri = (preset_dir / wp_file).resolve().as_uri()
                dump_text = _rewrite_wallpaper_uri(dump_text, new_uri)
            reset_result = run(["dconf", "reset", "-f", DCONF_PATH])
            if reset_result.returncode != 0:
                raise RuntimeError(f"dconf reset failed: {reset_result.stderr}")
            load_result = run(["dconf", "load", DCONF_PATH], input_data=dump_text)
            if load_result.returncode != 0:
                raise RuntimeError(f"dconf load failed: {load_result.stderr}")
            applied_anything = True
            warnings.append(
                "This preset was saved before per-category settings existed, "
                "so it was applied the old way (whole-tree), which may have "
                "also touched things like favorite-apps or keybindings. "
                "Re-save it to switch it to the safer, scoped format."
            )
            if selected_categories is not None and not all(selected_categories.values()):
                warnings.append(
                    "The category checklist above was ignored for this apply — "
                    "a preset this old has no per-category data to selectively "
                    "apply from, so everything in it was applied together."
                )
        except Exception as e:
            errors.append(f"dconf (legacy full-tree apply): {e}")

    # --- Files: theme assets, extensions/applets/desklets, panel-layout
    #     configs, per-app icon overrides. Each already fault-isolates its
    #     own items internally (see restore_assets etc.) — here we just
    #     make sure one whole category failing outright doesn't stop the
    #     next one. Filtered by category selection *before* handing off,
    #     so an unchecked category's files are never even touched.
    filtered_assets = {k: v for k, v in (meta.get("assets") or {}).items()
                        if _sel(ASSET_KIND_TO_CATEGORY.get(k, k))}
    filtered_addons = {k: v for k, v in (meta.get("addons") or {}).items()
                        if _sel(ADDON_KIND_TO_CATEGORY.get(k, k))}
    for restore_fn, filtered_meta, label in (
        (restore_assets, filtered_assets, "theme assets"),
        (restore_addons, filtered_addons, "extensions/applets/desklets"),
    ):
        try:
            missing, step_errors = restore_fn(preset_dir, filtered_meta)
            warnings.extend(missing)
            errors.extend(step_errors)
            if not step_errors:
                applied_anything = True
        except Exception as e:
            errors.append(f"{label}: {e}")

    for restore_fn, meta_key, category, label in (
        (restore_panel_layout, "panel", "panel", "panel/applet settings"),
        (restore_desktop_overrides, "desktop_overrides", "icons", "app icon overrides"),
    ):
        if not _sel(category):
            continue
        try:
            step_errors = restore_fn(preset_dir, meta.get(meta_key))
            errors.extend(step_errors)
        except Exception as e:
            errors.append(f"{label}: {e}")

    # Profile picture: no root needed (see module comment on
    # apply_profile_picture), so it belongs here in the main flow
    # alongside everything else, not gated behind a separate pkexec
    # dialog the way LightDM/Plymouth/GRUB are.
    if _sel("profile_picture"):
        try:
            apply_profile_picture(preset_dir, meta)
            applied_anything = True
        except FileNotFoundError:
            pass  # nothing was ever saved for this preset -- not an error
        except Exception as e:
            errors.append(f"profile picture: {e}")

    if not applied_anything:
        logger.error(f"apply '{name}': nothing could be applied — errors={errors}")
        raise RuntimeError(
            "Nothing could be applied — every step failed:\n- " + "\n- ".join(errors or ["(no details)"])
        )

    # Ask the running Cinnamon shell to restart itself so changes show
    # immediately, without logging the user out. Worth doing even on a
    # partial apply, so whatever DID succeed actually shows up.
    try:
        subprocess.Popen(
            ["cinnamon", "--replace"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError:
        pass

    logger.info(f"applied '{name}': warnings={len(warnings)} errors={len(errors)}"
                + (f" details={errors}" if errors else ""))
    return {"warnings": warnings, "errors": errors, "applied_anything": applied_anything}


def delete_preset(name):
    target = PRESETS_DIR / name
    if target.exists():
        shutil.rmtree(target)


def rename_preset(old, new):
    new = sanitize_name(new)
    if not new:
        raise ValueError("Preset name can't be empty.")
    old_dir = PRESETS_DIR / old
    new_dir = PRESETS_DIR / new
    if new_dir.exists():
        raise FileExistsError(f"A preset named '{new}' already exists.")
    old_dir.rename(new_dir)
    # meta.json's "name" mirrors the folder name (Phase 3 schema) — keep
    # them in sync so nothing reads a stale display name afterward.
    try:
        meta = load_meta(new)
        meta["name"] = new
        (new_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    except Exception:
        pass  # the rename itself already succeeded; a stale display name isn't worth failing over


# ---------------------------------------------------------------------------
# Phase 6 (part 1) — Export
#
# .tar.gz, not zip: cursor themes rely heavily on symlinks, and zipfile
# doesn't preserve those on extract, tarfile does natively. Each category's
# on-disk footprint is wherever save_preset() actually put it (see that
# function + bundle_assets()/bundle_addons()/save_lightdm() etc. for the
# authoritative layout) -- this table just names those same paths so an
# unchecked category can be left out of the archive entirely, not merely
# hidden in meta.json. Wallpaper is deliberately absent here: it's a single
# file living directly at the preset root with a variable extension
# (wallpaper.png / .jpg / ...), not a subfolder, so it's resolved from
# meta["wallpaper_file"] at export time instead of a static path.
# ---------------------------------------------------------------------------

CATEGORY_EXPORT_DIRS = {
    "style": ["assets/gtk", "assets/cinnamon", "addons/extensions"],
    "cursor": ["assets/cursor"],
    "icons": ["assets/icon", "desktop-overrides", "desktop-overrides-icons"],
    "fonts": [],
    "sounds": ["assets/sounds"],
    "wallpaper": [],
    "profile_picture": ["profile_picture"],
    "panel": ["addons/applets", "panel"],
    "widgets": ["addons/desklets"],
    "lightdm": ["system/lightdm"],
    "plymouth": ["system/plymouth"],
    "grub": ["system/grub"],
}


class ExportCancelled(Exception):
    """Raised by export_preset() when cancel_event fires between files.
    Not an error -- run_export_with_progress() checks for this specific
    type to show a neutral "cancelled" message instead of a red one."""
    pass


def _redact_meta_for_export(meta, selected):
    """Returns a deep-copied meta.json rewritten so every unselected
    category shows up as "skipped_on_purpose" -- the exact same shape
    save_preset() itself produces for a category the Save wizard's
    checklist left unchecked (see save_preset()'s _sel() branches).
    Reusing that shape is deliberate, not a shortcut: the roadmap calls
    for meta.json's status field to distinguish "skipped on export" from
    "not present on this system" using "the same status system as Phase
    3, not a separate mechanism" -- so a preset re-imported after being
    exported with GRUB unchecked looks exactly like one that was saved
    with GRUB unchecked in the first place, not like a third, novel
    state Import would need its own logic to understand."""
    meta = copy.deepcopy(meta)

    def _sel(cat):
        return selected.get(cat, True)

    dconf = meta.setdefault("dconf", {})
    for cat in DCONF_CATEGORIES:
        if not _sel(cat):
            dconf[cat] = {"keys": {}, "dirs": {}, "skipped_on_purpose": True}

    if not _sel("sounds"):
        meta["sound_files"] = {}
    if not _sel("wallpaper"):
        meta["wallpaper"] = {"status": "skipped_on_purpose"}
        meta.pop("wallpaper_file", None)
    if not _sel("profile_picture"):
        meta["profile_picture"] = {"status": "skipped_on_purpose"}
    if not _sel("lightdm"):
        meta["lightdm"] = {"status": "skipped_on_purpose"}
    if not _sel("plymouth"):
        meta["plymouth"] = {"status": "skipped_on_purpose"}
    if not _sel("grub"):
        meta["grub"] = {"status": "skipped_on_purpose"}
    if not _sel("panel"):
        meta["panel"] = {"status": "skipped_on_purpose", "applets": []}
    if not _sel("icons"):
        meta["desktop_overrides"] = {"status": "skipped_on_purpose", "files": [], "icons": []}

    assets = dict(meta.get("assets") or {})
    for kind, cat in ASSET_KIND_TO_CATEGORY.items():
        if not _sel(cat):
            assets.pop(kind, None)
    meta["assets"] = assets

    addons = dict(meta.get("addons") or {})
    for kind, cat in ADDON_KIND_TO_CATEGORY.items():
        if not _sel(cat):
            addons.pop(kind, None)
    meta["addons"] = addons

    # Recomputed last, same as save_preset() itself does, so it reflects
    # what this export actually contains rather than what the original
    # save contained.
    meta["categories"] = compute_category_statuses(meta)
    return meta


def export_preset(name, dest_path, selected_categories=None, cancel_event=None, progress_cb=None):
    """Writes preset `name` out as a .tar.gz at dest_path, with a single
    top-level `<name>/` directory inside the archive matching the
    on-disk preset layout exactly -- so Phase 6 part 2 (Import) can
    extract it straight into PRESETS_DIR/<name>/ with no translation
    step. selected_categories is the same {category: bool} shape the
    Save wizard's checklist already produces; a category missing from
    the dict defaults to True.

    Safe staged write: writes to `dest_path` + ".part" and only renames
    to the real filename via os.replace() (atomic, since both paths are
    in the same directory) on full success -- a cancelled or crashed
    export never leaves a half-written file at the real destination.
    cancel_event (a threading.Event) is checked between every single
    file, so Cancel is immediate; this function only ever *reads* from
    PRESETS_DIR, so cancelling can never touch the real preset.

    Raises ExportCancelled if cancel_event fires, FileNotFoundError if
    the preset doesn't exist, ValueError if it has no screenshot yet
    (export is blocked on this per the roadmap -- a preset with no
    screenshot, typically a not-yet-fixed-up import, needs a real
    thumbnail before it's worth handing to someone else)."""
    preset_dir = PRESETS_DIR / name
    if not preset_dir.is_dir():
        raise FileNotFoundError(f"No such preset: {name}")

    meta = load_meta(name)
    if (meta.get("screenshot") or {}).get("status") != "saved":
        raise ValueError("This preset has no screenshot yet — give it one before exporting.")

    selected = {} if selected_categories is None else selected_categories

    def _sel(cat):
        return selected.get(cat, True)

    redacted_meta = _redact_meta_for_export(meta, selected)

    # Build the full file list up front: gives progress_cb a real total
    # instead of a fake/estimated one, and surfaces a scan-time problem
    # before a single byte is written to the archive.
    files = [("meta.json", None)]  # written from redacted_meta, not copied off disk

    screenshot_file = (meta.get("screenshot") or {}).get("file") or SCREENSHOT_FILENAME
    if (preset_dir / screenshot_file).is_file():
        files.append((screenshot_file, preset_dir / screenshot_file))

    if _sel("wallpaper"):
        wp_file = meta.get("wallpaper_file")
        if wp_file and (preset_dir / wp_file).is_file():
            files.append((wp_file, preset_dir / wp_file))

    for cat, rel_dirs in CATEGORY_EXPORT_DIRS.items():
        if not _sel(cat):
            continue
        for rel in rel_dirs:
            src_dir = preset_dir / rel
            if not src_dir.is_dir():
                continue
            for path in sorted(src_dir.rglob("*")):
                # is_dir()/is_file() follow symlinks -- checking is_symlink()
                # FIRST is what keeps a symlinked directory (exactly the
                # case tar was picked over zip to handle) from being
                # silently treated as "just a directory" and skipped; it's
                # archived as its own symlink entry instead, same as a
                # symlinked file, via tar.add(..., recursive=False) below.
                if path.is_symlink() or path.is_file():
                    files.append((str(path.relative_to(preset_dir)), path))
                # else: a real (non-symlink) directory -- just a traversal
                # node for rglob, not its own archive entry.

    total = len(files)
    dest_path = Path(dest_path)
    tmp_path = dest_path.with_name(dest_path.name + ".part")
    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(tmp_path, "w:gz") as tar:
            for i, (arc_rel, src) in enumerate(files):
                if cancel_event is not None and cancel_event.is_set():
                    raise ExportCancelled()
                arcname = f"{name}/{arc_rel}"
                if src is None:
                    data = json.dumps(redacted_meta, indent=2).encode("utf-8")
                    info = tarfile.TarInfo(name=arcname)
                    info.size = len(data)
                    info.mtime = int(time.time())
                    tar.addfile(info, io.BytesIO(data))
                else:
                    tar.add(src, arcname=arcname, recursive=False)
                if progress_cb is not None:
                    progress_cb(i + 1, total)
        os.replace(tmp_path, dest_path)
    except BaseException:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise

    return dest_path


# ---------------------------------------------------------------------------
# Phase 6 (part 2) — Import
#
# Mirrors export_preset()'s safety shape rather than inventing a new one:
# staged write (extract into a private, same-filesystem staging dir, commit
# with one atomic rename), file-by-file iteration for real progress and a
# safe mid-operation cancel, and reuses run_export_with_progress()'s dialog
# rather than a second cancel-aware mechanism. The one-line rule this whole
# module exists to uphold: import only ever writes files to disk and never
# touches dconf, LightDM, Plymouth, or GRUB -- "never auto-applies anything"
# from the roadmap is enforced structurally here, not just documented,
# because nothing in this module calls anything from the apply-side code at
# all.
# ---------------------------------------------------------------------------

class ImportInvalidArchive(Exception):
    """Raised when the given file isn't a Cinnamon Presets export -- not a
    valid gzip/tar file, doesn't have the expected single-top-level-folder
    shape, is missing meta.json, or (via tarfile's own 'data' filter where
    available) contains a member that would land outside the extraction
    directory."""
    pass


class ImportCancelled(Exception):
    """Raised by import_preset() when cancel_event fires between members.
    Not an error -- the caller checks for this specific type to show a
    neutral "cancelled" message instead of a red one, same as
    ExportCancelled."""
    pass


def _is_within_directory(directory, target):
    directory = os.path.abspath(str(directory))
    target = os.path.abspath(str(target))
    return os.path.commonpath([directory]) == os.path.commonpath([directory, target])


def _peek_archive_name(archive_path):
    """Reads just the archive's member list -- no extraction -- to find its
    top-level preset name (the "<name>/meta.json" entry), so the GUI can
    check for a name collision and ask *before* spending time on the real
    extraction, rather than extracting into staging first and discovering
    the conflict only at the final rename. Raises ImportInvalidArchive if
    the archive doesn't have the expected shape."""
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            names = tar.getnames()
    except (tarfile.TarError, OSError) as e:
        raise ImportInvalidArchive(f"Not a valid Cinnamon Presets export: {e}")

    top_levels = {n.split("/", 1)[0] for n in names if n}
    if len(top_levels) != 1:
        raise ImportInvalidArchive(
            "Archive doesn't look like a single preset export "
            "(expected one top-level folder)."
        )
    candidate = next(iter(top_levels))
    if f"{candidate}/meta.json" not in names:
        raise ImportInvalidArchive("Archive is missing meta.json -- not a Cinnamon Presets export.")
    return candidate


def _peek_archive_meta(archive_path, top_level_name):
    """Reads just the <name>/meta.json member -- no extraction of anything
    else -- so the Import preview dialog can show the preset name and
    which categories are actually in the archive before committing to the
    real (potentially large) extraction."""
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            member = tar.getmember(f"{top_level_name}/meta.json")
            f = tar.extractfile(member)
            if f is None:
                raise ImportInvalidArchive("Archive's meta.json couldn't be read.")
            return json.loads(f.read().decode("utf-8"))
    except (tarfile.TarError, OSError, KeyError, json.JSONDecodeError) as e:
        raise ImportInvalidArchive(f"Couldn't read archive metadata: {e}")


def import_preset(archive_path, final_name, cancel_event=None, progress_cb=None):
    """Extracts a .tar.gz preset archive (written by export_preset()) into
    PRESETS_DIR/<final_name>/. final_name is decided by the caller (GUI)
    BEFORE this runs -- typically the archive's own name via
    _peek_archive_name(), or a renamed one if that name already exists --
    so this function never has to improvise a rename mid-extraction; it
    fails loudly with FileExistsError if final_name is already taken
    rather than silently overwriting or auto-suffixing.

    Safe staged extract: everything is written into a private staging
    directory -- tempfile.mkdtemp(dir=PRESETS_DIR), so it's on the same
    filesystem as the real presets dir -- first. Only on full,
    uninterrupted success does the staging directory's single preset
    folder get renamed into place with one instant os.rename(), not a
    copy; the real preset tree is never touched before that one atomic
    step, and a cancelled or failed import just deletes the staging
    directory, leaving PRESETS_DIR exactly as it was.

    File-by-file iteration (tar.extract() per member, not
    tarfile.extractall()), both so progress_cb(current, total) has real
    numbers and so cancel_event is checked between every single member,
    the same shape export_preset() already uses. Each member's path is
    checked against the staging directory before extraction (defends
    against a malicious/corrupted archive using '../' entries to write
    outside it); Python 3.12's tarfile 'data' extraction filter is used
    when available for the same reason plus symlink-target and
    special-file checks this function doesn't duplicate by hand."""
    final_name = sanitize_name(final_name)
    if not final_name:
        raise ValueError("Preset name can't be empty.")
    if (PRESETS_DIR / final_name).exists():
        raise FileExistsError(f"A preset named '{final_name}' already exists.")

    ensure_dirs()
    staging_root = Path(tempfile.mkdtemp(prefix=".importing-", dir=str(PRESETS_DIR)))
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            members = tar.getmembers()
            top_levels = {m.name.split("/", 1)[0] for m in members if m.name}
            if len(top_levels) != 1:
                raise ImportInvalidArchive(
                    "Archive doesn't look like a single preset export "
                    "(expected one top-level folder)."
                )
            archive_name = next(iter(top_levels))
            if not any(m.name == f"{archive_name}/meta.json" for m in members):
                raise ImportInvalidArchive(
                    "Archive is missing meta.json -- not a Cinnamon Presets export."
                )

            total = len(members)
            for i, member in enumerate(members):
                if cancel_event is not None and cancel_event.is_set():
                    raise ImportCancelled()
                if not _is_within_directory(staging_root, staging_root / member.name):
                    raise ImportInvalidArchive(f"Archive contains an unsafe path: {member.name}")
                try:
                    tar.extract(member, path=staging_root, filter="data")
                except TypeError:
                    # Python < 3.12 doesn't have the filter parameter yet --
                    # the manual path check above still covers the main risk.
                    tar.extract(member, path=staging_root)
                if progress_cb is not None:
                    progress_cb(i + 1, total)

        extracted_dir = staging_root / archive_name
        if not extracted_dir.is_dir():
            raise ImportInvalidArchive("Archive extraction did not produce the expected folder.")

        # meta.json's "name" mirrors the folder name (Phase 3 schema, same
        # invariant rename_preset() maintains) -- keep them in sync if the
        # final name differs from what the archive itself was named.
        if final_name != archive_name:
            meta_path = extracted_dir / "meta.json"
            try:
                meta = json.loads(meta_path.read_text())
                meta["name"] = final_name
                meta_path.write_text(json.dumps(meta, indent=2))
            except Exception:
                pass  # extraction already succeeded -- a stale display name isn't worth failing the whole import over

        dest_dir = PRESETS_DIR / final_name
        os.rename(extracted_dir, dest_dir)  # same filesystem -- instant, not a copy
        return dest_dir
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Update checking
# ---------------------------------------------------------------------------

def _parse_repo_slug(url):
    """Turn https://github.com/user/repo into 'user/repo', or None."""
    if not url:
        return None
    m = re.search(r"github\.com/([^/]+/[^/]+?)(?:\.git)?/?$", url.strip())
    return m.group(1) if m else None


def _script_git_root():
    """If this script lives inside a git checkout, return that folder."""
    here = Path(__file__).resolve().parent
    if (here / ".git").is_dir():
        return here
    return None


def check_for_updates(timeout=6):
    """
    Returns a dict describing the result:
      {"status": "up_to_date"}
      {"status": "update_available", "latest": "v0.3", "url": "..."}
      {"status": "error", "message": "..."}
      {"status": "not_configured"}
    """
    slug = _parse_repo_slug(GITHUB_REPO_URL)
    if not slug:
        return {"status": "not_configured"}

    api_url = f"https://api.github.com/repos/{slug}/releases/latest"
    try:
        req = urllib.request.Request(
            api_url, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        latest_tag = data.get("tag_name", "").strip()
        release_url = data.get("html_url", GITHUB_REPO_URL)
    except Exception as e:
        logger.warning(f"update check failed: {e}")
        return {"status": "error", "message": str(e)}

    if not latest_tag:
        logger.warning("update check: no release tag found in API response")
        return {"status": "error", "message": "No release tag found."}

    normalized_latest = latest_tag.lstrip("vV")
    normalized_current = VERSION.lstrip("vV")

    if normalized_latest == normalized_current:
        logger.info(f"update check: up to date ({VERSION})")
        return {"status": "up_to_date"}
    logger.info(f"update check: update available ({VERSION} -> {latest_tag})")
    return {"status": "update_available", "latest": latest_tag, "url": release_url}


def perform_git_update():
    """
    If this install is a git checkout, `git pull` it in place and return
    (True, message). Otherwise return (False, message) so the caller can
    fall back to opening the releases page instead.
    """
    root = _script_git_root()
    if not root:
        return False, "Not a git checkout — can't self-update in place."

    result = run(["git", "-C", str(root), "pull", "--ff-only"])
    if result.returncode != 0:
        return False, f"git pull failed:\n{result.stderr.strip()}"
    return True, result.stdout.strip() or "Already up to date."


def _is_appimage():
    """Roadmap Phase 8's AppImage item is explicitly a secondary,
    optional-future distribution path -- there's no build system in this
    project producing an AppImage yet, so there's nothing real to
    download-and-swap. This just lets the update flow recognize the
    situation and say so plainly instead of showing the generic
    "not a git checkout" message, which would be confusing/wrong for
    someone who didn't clone anything."""
    return bool(os.environ.get("APPIMAGE"))


def _load_last_update_check_time():
    try:
        data = json.loads(UPDATE_CHECK_STATE_FILE.read_text())
        return float(data.get("last_check_at", 0))
    except Exception:
        return 0.0


def _save_last_update_check_time():
    try:
        UPDATE_CHECK_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        UPDATE_CHECK_STATE_FILE.write_text(json.dumps({"last_check_at": time.time()}))
    except Exception:
        pass  # non-critical -- worst case the silent check just runs a bit more often than intended


def _should_auto_check_updates():
    """The manual "Check Now" button always bypasses this and checks
    immediately regardless -- this only gates the silent startup
    check."""
    return (time.time() - _load_last_update_check_time()) >= UPDATE_CHECK_INTERVAL_SECONDS


def restart_process():
    """Roadmap Phase 8: after a successful self-update, relaunch in
    place via os.execv rather than telling the person to close and
    reopen the app themselves. This replaces the current process image
    entirely -- re-importing modules in the same interpreter wouldn't
    pick up the change, since Python's already loaded the old bytecode
    for everything into memory. Never returns on success."""
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ---------------------------------------------------------------------------
# Phase 2: Screenshot Capture Module
#
# Standalone here on purpose (per the roadmap) — the Save wizard (Phase 4)
# and the main list's thumbnails (Phase 3) both just construct a
# ScreenshotCaptureFlow and call .start(); neither reimplements any of
# this. Deliberately no external screenshot utility dependency (no
# gnome-screenshot, no scrot, no import(1)) — capture goes straight
# through GDK, which this app already depends on for its own window.
# ---------------------------------------------------------------------------

SCREENSHOT_COUNTDOWN_SECONDS = 4  # within the roadmap's ~3-5s window
SCREENSHOT_FILENAME = "screenshot.png"


def capture_screen_pixbuf():
    """Grab the whole screen as a GdkPixbuf directly off the root window
    — the same mechanism GTK itself uses internally, no external tool
    involved. Raises with a real message on failure instead of quietly
    returning a blank/partial image, so callers can surface it."""
    root = Gdk.get_default_root_window()
    if root is None:
        raise RuntimeError("Couldn't access the root window to capture the screen.")
    width, height = root.get_width(), root.get_height()
    pixbuf = Gdk.pixbuf_get_from_window(root, 0, 0, width, height)
    if pixbuf is None:
        raise RuntimeError("Screen capture returned no image data.")
    return pixbuf


def save_screenshot(preset_dir, pixbuf):
    """Save a captured screenshot into the preset folder, alongside the
    other bundled assets (theme files, addon files, the wallpaper copy,
    etc). Always the same filename, so later phases (list thumbnails,
    export/import) have one predictable path to look for instead of
    needing their own naming convention."""
    dest = Path(preset_dir) / SCREENSHOT_FILENAME
    pixbuf.savev(str(dest), "png", [], [])
    return dest


def _scale_pixbuf_to_fit(pixbuf, max_w, max_h):
    """Downscale for on-screen preview only — never touches the actual
    saved file, which always keeps the full-resolution capture."""
    w, h = pixbuf.get_width(), pixbuf.get_height()
    scale = min(max_w / w, max_h / h, 1.0)
    if scale >= 1.0:
        return pixbuf
    return pixbuf.scale_simple(max(1, int(w * scale)), max(1, int(h * scale)),
                                GdkPixbuf.InterpType.BILINEAR)


# ---------------------------------------------------------------------------
# Phase 3: thumbnails — a real screenshot if the preset has one, otherwise a
# deterministic gradient placeholder (same seed text -> same colors, every
# time), matching the color-block placeholders in the design mockups.
# ---------------------------------------------------------------------------

def _gradient_colors_for_seed(seed):
    """Two RGB colors derived from a hash of `seed`, so the same preset
    name always produces the same-looking placeholder (deterministic,
    no randomness/state needed) while different names look visually
    distinct from each other."""
    digest = hashlib.sha256((seed or "").encode("utf-8")).digest()
    hue1 = digest[0] / 255.0
    hue2 = (digest[1] / 255.0 * 0.5 + hue1 + 0.25) % 1.0  # offset so the two ends actually differ
    lightness = 0.55 + (digest[2] / 255.0) * 0.15
    saturation = 0.55 + (digest[3] / 255.0) * 0.35
    rgb1 = colorsys.hls_to_rgb(hue1, lightness, saturation)
    rgb2 = colorsys.hls_to_rgb(hue2, lightness * 0.85, saturation)
    return rgb1, rgb2


def render_gradient_placeholder(seed_text, width, height):
    """Returns a GdkPixbuf of a diagonal two-color gradient, seeded off
    `seed_text` (typically the preset's display name). Pure function, no
    disk access — nothing is cached to a file, it's cheap enough to
    regenerate on the fly whenever the list needs it."""
    width, height = max(1, int(width)), max(1, int(height))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    (r1, g1, b1), (r2, g2, b2) = _gradient_colors_for_seed(seed_text)
    gradient = cairo.LinearGradient(0, 0, width, height)
    gradient.add_color_stop_rgb(0, r1, g1, b1)
    gradient.add_color_stop_rgb(1, r2, g2, b2)
    ctx.set_source(gradient)
    ctx.rectangle(0, 0, width, height)
    ctx.fill()
    return Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)


# ---------------------------------------------------------------------------
# Category icons: custom hand-drawn art first (once it exists), then a
# matching system/Cinnamon-Settings icon, then the gradient placeholder as
# a last resort so a category never renders completely blank.
#
# WHERE TO PUT CUSTOM ART: icons/categories/<category>.svg (or .png),
# right next to the existing icons/cinnamon-presets.svg. Checked in both
# a source checkout AND an installed copy (see install.sh, which mirrors
# this folder into ~/.local/share/cinnamon-presets/icons/categories/ the
# same way it already installs the main app icon) — drop a file in named
# after any key in CATEGORY_ORDER (e.g. "grub.svg", "plymouth.svg") and
# it's picked up automatically next run, no code changes needed.
#
# Two categories have NO reasonable system icon to fall back to at all,
# so they'll show the gradient placeholder until custom art exists:
# "plymouth" (Boot Animation) and "grub" (GRUB Bootloader). Everything
# else already has a decent placeholder from Cinnamon's own Settings app
# or the standard freedesktop icon set, and custom art is optional there.
# ---------------------------------------------------------------------------

CATEGORY_ICON_DIR_CANDIDATES = [
    Path(__file__).resolve().parent / "icons" / "categories",           # running from a source checkout
    Path.home() / ".local/share/cinnamon-presets/icons/categories",     # installed via install.sh
]

CATEGORY_SYSTEM_ICON_NAMES = {
    "style": ["cs-themes", "preferences-desktop-theme"],
    "cursor": ["input-mouse"],
    "icons": ["preferences-desktop-icons", "view-grid-symbolic"],
    "fonts": ["preferences-desktop-font", "font-x-generic"],
    "sounds": ["preferences-desktop-multimedia", "audio-volume-high"],
    "wallpaper": ["cs-backgrounds", "preferences-desktop-wallpaper"],
    "profile_picture": ["avatar-default", "system-users"],
    "panel": ["user-desktop"],  # "cs-panel" is already tried earlier by
                                 # render_panel_icon() -- see the Live
                                 # theme previews section below
    "widgets": ["cs-desklets", "applications-accessories"],
    "lightdm": ["system-lock-screen", "system-users"],
    "plymouth": [],  # no sensible system icon exists — needs custom art
    "grub": [],      # same
}


def _find_category_icon_file(cat):
    for base in CATEGORY_ICON_DIR_CANDIDATES:
        for ext in (".svg", ".png", ".jpg", ".jpeg"):
            candidate = base / f"{cat}{ext}"
            if candidate.is_file():
                return candidate
    return None


def _letterbox_to_square(pixbuf, size):
    """Center pixbuf on a transparent size x size canvas. Every category
    icon in the row is drawn at the same fixed size, so a custom asset
    that isn't square (e.g. a wide Windows-7-style glyph) needs this to
    read as the same visual weight as its square/symbolic neighbors —
    new_from_file_at_scale()'s preserve_aspect_ratio alone just shrinks
    it to fit *inside* the box, it doesn't recenter it in the box."""
    canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, size, size)
    canvas.fill(0x00000000)
    pw, ph = pixbuf.get_width(), pixbuf.get_height()
    off_x, off_y = (size - pw) // 2, (size - ph) // 2
    pixbuf.composite(
        canvas, off_x, off_y, pw, ph, off_x, off_y, 1.0, 1.0,
        GdkPixbuf.InterpType.BILINEAR, 255,
    )
    return canvas


def load_category_icon_pixbuf(cat, size):
    theme = Gtk.IconTheme.get_default()
    for name in CATEGORY_SYSTEM_ICON_NAMES.get(cat, []):
        try:
            if theme.has_icon(name):
                return theme.load_icon(name, size, Gtk.IconLookupFlags.FORCE_SIZE)
        except GLib.Error:
            continue

    custom = _find_category_icon_file(cat)
    if custom is not None:
        try:
            loaded = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(custom), size, size, True)
            if loaded is not None:
                if loaded.get_width() != size or loaded.get_height() != size:
                    loaded = _letterbox_to_square(loaded, size)
                return loaded
        except GLib.Error:
            pass  # fall through to the gradient placeholder below

    return render_gradient_placeholder(cat, size, size)


# ---------------------------------------------------------------------------
# General UI icons (toolbar/action buttons) — separate namespace from the
# category swatches above, since these are a different kind of icon
# entirely (interface actions, not theme-category illustrations). Same
# "custom art first, then a system fallback, then nothing" pattern, except
# the final fallback here is None (plain text button) rather than a
# gradient placeholder — a colored square would look like an error on a
# toolbar button, whereas it reads fine as a stand-in preset thumbnail.
#
# Covers Import/Export now. Settings, "+ Save New Preset", and the footer's
# Patreon/YouTube/GitHub logos are all planned to use this same mechanism
# later — just add a name to UI_SYSTEM_ICON_NAMES and/or drop a file in
# icons/ui/ whenever that art exists, no new plumbing needed.
# ---------------------------------------------------------------------------

UI_ICON_DIR_CANDIDATES = [
    Path(__file__).resolve().parent / "icons" / "ui",
    Path.home() / ".local/share/cinnamon-presets/icons/ui",
]

UI_SYSTEM_ICON_NAMES = {
    "import": ["document-import", "go-down"],
    "export": ["document-export", "document-send", "go-up"],
    "settings": ["preferences-system", "emblem-system"],
    "save": ["list-add", "document-save"],
}


def _find_ui_icon_file(name):
    for base in UI_ICON_DIR_CANDIDATES:
        for ext in (".svg", ".png", ".jpg", ".jpeg"):
            candidate = base / f"{name}{ext}"
            if candidate.is_file():
                return candidate
    return None


def load_ui_icon_pixbuf(name, size):
    custom = _find_ui_icon_file(name)
    if custom is not None:
        try:
            loaded = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(custom), size, size, True)
            if loaded is not None:
                return loaded
        except GLib.Error:
            pass

    theme = Gtk.IconTheme.get_default()
    for icon_name in UI_SYSTEM_ICON_NAMES.get(name, []):
        try:
            if theme.has_icon(icon_name):
                return theme.load_icon(icon_name, size, Gtk.IconLookupFlags.FORCE_SIZE)
        except GLib.Error:
            continue

    return None  # caller falls back to a plain text-only button


def build_icon_text_button(ui_icon_name, label_text, size=16):
    """A Gtk.Button with an icon + label, icon optional -- uses
    load_ui_icon_pixbuf()'s "nothing found yet" case to degrade to a
    plain text button instead of showing a broken/missing image."""
    pixbuf = load_ui_icon_pixbuf(ui_icon_name, size)
    button = Gtk.Button()
    if pixbuf is not None:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_halign(Gtk.Align.CENTER)
        box.pack_start(Gtk.Image.new_from_pixbuf(pixbuf), False, False, 0)
        box.pack_start(Gtk.Label(label=label_text), False, False, 0)
        button.add(box)
    else:
        button.set_label(label_text)
    return button


# ---------------------------------------------------------------------------
# Live theme previews for Cursor / Icons / Panel / Profile Picture, the same
# idea as Cinnamon Settings' own Themes page (see the screenshot that
# prompted this): show what's actually currently active, not just a
# generic icon representing "this row is about cursors." All four are
# best-effort and layer ON TOP of load_category_icon_pixbuf()'s existing
# chain -- if a live preview isn't available for any reason (non-X11
# session, theme with no readable cursor image, no avatar set, etc.), the
# category icon (custom art -> system icon -> gradient) is exactly what
# gets shown instead, so this can never make a row look worse than it
# already did.
#
# Cursor and Icons come straight from GDK/GTK's own live theme state --
# our app is itself a running GTK3 process on the same Cinnamon session,
# so Gtk.Settings/Gtk.IconTheme already track the active cursor-theme/
# icon-theme via XSETTINGS the same way every other GTK app does, no
# custom Xcursor-file parsing or screenshot analysis needed. Panel
# resolves "cs-panel" -- Cinnamon Settings' own icon name for its Panel
# module page, which any icon theme aiming to look native inside Cinnamon
# (including complete/retro packs like Mint-7 and Mint-XP) ships alongside
# its other cs-* Settings icons. Profile Picture reuses
# _accounts_get_icon_file() -- the exact same AccountsService IconFile
# lookup save_profile_picture() itself uses, rather than a fresh assumption
# about where the avatar file lives. None of the four need a screenshot to
# exist first.
# ---------------------------------------------------------------------------

def _trim_transparent_margin(pixbuf):
    """Crops to the bounding box of the pixbuf's non-transparent pixels.
    Cursor glyphs are the motivating case: an arrow's ink sits up near
    one corner of its canvas, with mostly-empty space padding out the
    rest so the hotspot has room to be anywhere on it. Returns the
    pixbuf unchanged if it has no alpha channel, or if every pixel
    turned out transparent (nothing sensible to crop to)."""
    if not pixbuf.get_has_alpha():
        return pixbuf
    w, h = pixbuf.get_width(), pixbuf.get_height()
    if w <= 0 or h <= 0:
        return pixbuf
    pixels = pixbuf.get_pixels()
    stride = pixbuf.get_rowstride()
    n_channels = pixbuf.get_n_channels()
    min_x, min_y, max_x, max_y = w, h, -1, -1
    for row in range(h):
        base = row * stride
        for col in range(w):
            if pixels[base + col * n_channels + 3] > 8:  # ignore near-zero alpha noise
                if col < min_x: min_x = col
                if col > max_x: max_x = col
                if row < min_y: min_y = row
                if row > max_y: max_y = row
    if max_x < min_x or max_y < min_y:
        return pixbuf  # fully transparent -- nothing to trim
    return pixbuf.new_subpixbuf(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)


def render_cursor_preview(size):
    """Best-effort live preview of the currently active cursor theme,
    for the small checklist-row icon slot -- a DIFFERENT concern from
    capture_cursor_overlay()'s screenshot compositing, and doesn't touch
    it. Scaling the raw cursor bitmap straight into a square slot looks
    lopsided next to the other, already-centered row icons, because the
    glyph itself isn't centered on its own canvas (see
    _trim_transparent_margin's docstring) -- how far off depends on how
    much padding that particular theme happens to bake in, hence
    varying by theme. Trimming to just the visible glyph and
    re-centering fixes that; it has nothing to do with hotspots.
    Returns None (caller falls back to the category icon) if GDK can't
    hand back cursor image data -- most commonly because the session
    isn't X11, or the active theme has no image GDK can extract."""
    try:
        display = Gdk.Display.get_default()
        if display is None:
            return None
        for cursor_name in ("default", "left_ptr"):
            cursor = Gdk.Cursor.new_from_name(display, cursor_name)
            if cursor is None:
                continue
            pixbuf = cursor.get_image()
            if pixbuf is None:
                continue
            trimmed = _trim_transparent_margin(pixbuf)
            tw, th = trimmed.get_width(), trimmed.get_height()
            if tw <= 0 or th <= 0:
                continue
            # A small margin (not edge-to-edge) so it reads at roughly
            # the same visual weight as the other row icons, whether
            # this theme's native glyph is tiny or oversized.
            target = max(1, round(size * 0.8))
            scale = min(target / tw, target / th)
            scaled = trimmed.scale_simple(
                max(1, round(tw * scale)), max(1, round(th * scale)),
                GdkPixbuf.InterpType.BILINEAR,
            )
            if scaled is not None:
                return _letterbox_to_square(scaled, size)
    except Exception:
        pass
    return None


def render_icon_preview(size):
    """Best-effort live preview of the currently active icon theme, using
    the same 'folder' icon Cinnamon Settings' own Themes page shows.
    Returns None (caller falls back to the category icon) if the active
    icon theme has no folder icon GTK can resolve, which shouldn't
    normally happen but is cheap to guard against anyway."""
    try:
        theme = Gtk.IconTheme.get_default()
        if theme is None or not theme.has_icon("folder"):
            return None
        return theme.load_icon("folder", size, Gtk.IconLookupFlags.FORCE_SIZE)
    except Exception:
        return None


def render_profile_picture_preview(size):
    """Best-effort live preview of the actual active account avatar.
    Deliberately reuses _accounts_get_icon_file() -- the same
    AccountsService IconFile lookup save_profile_picture() itself uses
    -- rather than assuming the file lives at ~/.face. That file's a
    legacy convention some tools still check, but Mint's own avatar
    picker (and accountsservice generally) actually stores the current
    icon at /var/lib/AccountsService/icons/<user>; IconFile is the one
    property guaranteed to point at wherever it really is. Keeping both
    the preview and the save path on the same lookup also means they
    can't quietly drift apart from each other. Returns None (caller
    falls back to the static avatar-default/gradient chain) if no icon
    is set or the file it points to isn't readable."""
    try:
        icon_path = _accounts_get_icon_file()
        if not icon_path or not Path(icon_path).is_file():
            return None
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, size, size, True)
        if pixbuf is None:
            return None
        if pixbuf.get_width() != size or pixbuf.get_height() != size:
            pixbuf = _letterbox_to_square(pixbuf, size)
        return pixbuf
    except Exception:
        return None


def render_panel_icon(size):
    """Best-effort live preview of the panel as a whole. Tries, in order:

    1. 'cs-panel' -- Cinnamon Settings' own icon for its Panel module
       page. Any icon theme meant to look native inside Cinnamon Settings
       (which includes complete/retro packs like Mint-7 and Mint-XP, not
       just Cinnamon's own Mint-Y/Mint-X) ships this alongside its other
       cs-* Settings icons, so it's the closest thing to a theme actually
       depicting 'the panel' rather than just a piece of it.
    2. The icon-naming-spec 'start-here' family (Mint's colored orb,
       Ubuntu's circle-of-friends, a Windows-style pack's start button --
       all live under this name) -- not the panel itself, but the most
       recognizable panel-adjacent glyph for themes that don't customize
       cs-panel specifically.

    Resolves straight from the active GTK icon theme either way, so it's
    always square, always theme-accurate, and needs no screenshot to
    exist first. Returns None (caller falls back to the static category
    icon) if neither is available."""
    try:
        theme = Gtk.IconTheme.get_default()
        if theme is None:
            return None
        for name in ("cs-panel", "start-here", "start-here-symbolic",
                     "distributor-logo", "system-run"):
            if theme.has_icon(name):
                return theme.load_icon(name, size, Gtk.IconLookupFlags.FORCE_SIZE)
    except Exception:
        pass
    return None


def category_swatch_pixbuf(cat, size):
    """Prefer a live preview of what's actually currently active for the
    categories where that's meaningful (Cursor, Icons, Panel, Profile
    Picture); everything else, and anything a live preview couldn't be
    produced for, falls back to the existing category-icon chain (custom
    art -> system icon -> gradient) — so this can never make a row look
    worse than it already did before live previews existed. All four
    resolve straight from live system/theme state (GTK icon theme, cursor
    state, or AccountsService), no screenshot needed for any of them.

    Shared by SavePresetWizard and ApplyPresetDialog so the same category
    always renders the same icon in both places — per the roadmap's "same
    icons, same layout" checklist design, this is the one place that
    mapping lives instead of two copies that could drift apart."""
    if cat == "cursor":
        preview = render_cursor_preview(size)
        if preview is not None:
            return preview
    elif cat == "icons":
        preview = render_icon_preview(size)
        if preview is not None:
            return preview
    elif cat == "panel":
        preview = render_panel_icon(size)
        if preview is not None:
            return preview
    elif cat == "profile_picture":
        preview = render_profile_picture_preview(size)
        if preview is not None:
            return preview
    return load_category_icon_pixbuf(cat, size)


def build_dialog_title_header(title_text, preset_name):
    """Big centered bold title + centered gray preset name below it --
    shared by Apply/Export/Import so the three "do something with a
    preset" dialogs read as one consistent design language instead of
    each having its own slightly different header treatment."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    box.set_margin_bottom(6)

    title_label = Gtk.Label(xalign=0.5)
    title_label.set_justify(Gtk.Justification.CENTER)
    title_label.set_halign(Gtk.Align.CENTER)
    title_label.set_markup(f"<span size='x-large' weight='bold'>{GLib.markup_escape_text(title_text)}</span>")
    box.pack_start(title_label, False, False, 0)

    name_label = Gtk.Label(xalign=0.5)
    name_label.set_justify(Gtk.Justification.CENTER)
    name_label.set_halign(Gtk.Align.CENTER)
    name_label.set_markup(f"<span foreground='#767676'>{GLib.markup_escape_text(preset_name)}</span>")
    box.pack_start(name_label, False, False, 0)

    return box


def build_category_checklist_row(cat, size, initial_checked, status_note=None):
    """Shared checklist-row builder for the 12-category checklist reused
    verbatim across Save (Phase 4), Apply (Phase 5), and Export (Phase
    6) -- same icon, same label, same description everywhere, per the
    roadmap's "same visual language" design goal: learn this row once,
    recognize it in all three places. Previously duplicated as a
    private _build_category_row() method on both SavePresetWizard and
    ApplyPresetDialog (same risk category_swatch_pixbuf() above was
    already extracted to avoid); pulled out here instead of adding a
    third copy for ExportDialog.

    Only what actually varies between the three callers is a parameter:
    the swatch size, whether the box starts checked, and an optional
    dim status note (Apply's "not saved" / "nothing to apply", Export's
    own equivalent notes). Returns (row_widget, check_button) -- the
    caller stores the checkbox reference and packs the row itself."""
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

    swatch = Gtk.Image.new_from_pixbuf(category_swatch_pixbuf(cat, size))
    row.pack_start(swatch, False, False, 0)

    text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
    title_label = Gtk.Label(xalign=0)
    title_label.set_markup(f"<b>{GLib.markup_escape_text(CATEGORY_UI_LABELS[cat])}</b>")
    text_box.pack_start(title_label, False, False, 0)
    desc_label = Gtk.Label(label=CATEGORY_DESCRIPTIONS.get(cat, ""), xalign=0)
    desc_label.set_line_wrap(True)
    desc_label.set_max_width_chars(45)
    desc_label.get_style_context().add_class("dim-label")
    text_box.pack_start(desc_label, False, False, 0)
    row.pack_start(text_box, True, True, 0)

    if status_note:
        note = Gtk.Label(label=status_note, xalign=1)
        note.get_style_context().add_class("dim-label")
        row.pack_start(note, False, False, 0)

    check = Gtk.CheckButton()
    check.set_active(initial_checked)
    check.set_valign(Gtk.Align.CENTER)
    row.pack_start(check, False, False, 0)

    return row, check


def load_thumbnail_pixbuf(preset_dir, meta, width, height):
    """The one place both grid and list view ask for a preset's thumbnail.
    Real screenshot if there is one and it's still readable; a
    deterministic gradient placeholder otherwise — this is meant to
    "mainly only occur on imports" per the roadmap, but also covers any
    preset saved with the screenshot prompt declined."""
    shot = (meta or {}).get("screenshot") or {}
    if shot.get("status") == "saved" and shot.get("file"):
        path = Path(preset_dir) / shot["file"]
        if path.is_file():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(path), width, height, True,
                )
                if pixbuf is not None:
                    return pixbuf
            except GLib.Error:
                pass  # corrupt/unreadable file — fall through to the placeholder
    seed = (meta or {}).get("name") or Path(preset_dir).name
    return render_gradient_placeholder(seed, width, height)


def capture_cursor_overlay():
    """Best-effort pointer position + cursor glyph, in the same root-
    window coordinates the screen capture itself uses. Returns None if
    either piece isn't available on this system — showing the cursor is
    opt-in, so it's fine for this to just come up empty and leave the
    checkbox in the review dialog hidden.

    No XFixes/ctypes needed: Gdk.Cursor.get_image() already hands back
    GDK's own cursor-theme pixbuf for a named cursor, which is enough to
    draw a representative pointer glyph — it won't reflect exactly which
    cursor (text/resize/etc.) was under the pointer at that instant, but
    for a desktop-look screenshot that's not the point; showing roughly
    where the mouse was is."""
    display = Gdk.Display.get_default()
    if display is None:
        return None
    seat = display.get_default_seat()
    pointer = seat.get_pointer() if seat else None
    root = Gdk.get_default_root_window()
    if pointer is None or root is None:
        return None

    try:
        _, x, y, _ = root.get_device_position(pointer)
    except Exception:
        return None

    # get_surface() (not get_image() + get_option("x_hot"/"y_hot")) on
    # purpose: get_image()'s hotspot is read back from text metadata baked
    # into the cursor's *nominal* bitmap, which isn't necessarily the size
    # GDK actually rendered here. A theme that only ships e.g. 32px cursors
    # while the display asks for 24px gets scaled down, and get_image()
    # doesn't scale x_hot/y_hot to match — so the tip drifts off-center,
    # and how far depends on how mismatched that theme's native size is
    # from the requested one (fine for a theme that already matches,
    # visibly off for one that doesn't). get_surface() returns hot_x/hot_y
    # as out-params computed for the exact surface it hands back, so
    # they're correct regardless of the theme's native size or any HiDPI
    # scale factor.
    try:
        cursor = Gdk.Cursor.new_from_name(display, "default")
        surface, hot_x, hot_y = cursor.get_surface() if cursor else (None, 0, 0)
    except Exception:
        surface = None
    if surface is None:
        return None

    cursor_pixbuf = Gdk.pixbuf_get_from_surface(
        surface, 0, 0, surface.get_width(), surface.get_height(),
    )
    if cursor_pixbuf is None:
        return None

    # get_surface()'s hot_x/hot_y are in the surface's own (possibly
    # HiDPI-scaled) *user-space* units, but pixbuf_get_from_surface()
    # above copies its *raw pixel buffer*, which is user-space size
    # times the surface's device scale. If a theme gets rendered onto a
    # surface with a device scale other than 1 -- which can happen per
    # cursor depending on which nominal size that theme actually ships,
    # not just on HiDPI displays -- hot_x/hot_y need multiplying by that
    # same scale to land on the right pixel in the buffer we just made,
    # or the drawn glyph and the recorded hotspot silently drift apart.
    try:
        scale_x, scale_y = surface.get_device_scale()
    except Exception:
        scale_x, scale_y = 1.0, 1.0

    if os.environ.get("CINNAMON_PRESETS_DEBUG"):
        print(
            f"[cursor-debug] pointer=({x},{y}) raw_hot=({hot_x},{hot_y}) "
            f"device_scale=({scale_x},{scale_y}) "
            f"surface_px=({surface.get_width()},{surface.get_height()}) "
            f"pixbuf_px=({cursor_pixbuf.get_width()},{cursor_pixbuf.get_height()})",
            file=sys.stderr,
        )

    try:
        hot_x = int(round(hot_x * scale_x))
        hot_y = int(round(hot_y * scale_y))
    except (TypeError, ValueError):
        hot_x, hot_y = 0, 0

    return {"pixbuf": cursor_pixbuf, "hotspot": (hot_x, hot_y), "position": (x, y)}


def composite_cursor_onto(pixbuf, cursor_pixbuf, hotspot, x, y):
    """Returns a NEW pixbuf (the original is left untouched) with the
    cursor glyph drawn at (x, y) — root-window coordinates, same as the
    screenshot's own — offset by the cursor's hotspot so its tip lines
    up with where the pointer actually was."""
    result = pixbuf.copy()
    hot_x, hot_y = hotspot
    dest_x, dest_y = x - hot_x, y - hot_y
    cw, ch = cursor_pixbuf.get_width(), cursor_pixbuf.get_height()
    pw, ph = result.get_width(), result.get_height()

    # Clip to the destination's bounds — the pointer can sit right at a
    # screen edge, and composite() expects an in-bounds rectangle.
    clip_x, clip_y = max(0, dest_x), max(0, dest_y)
    clip_w = min(cw - (clip_x - dest_x), pw - clip_x)
    clip_h = min(ch - (clip_y - dest_y), ph - clip_y)
    if clip_w <= 0 or clip_h <= 0:
        return result

    cursor_pixbuf.composite(
        result, clip_x, clip_y, clip_w, clip_h,
        dest_x, dest_y, 1.0, 1.0,
        GdkPixbuf.InterpType.NEAREST, 255,
    )
    return result


class _CountdownOverlay(Gtk.Window):
    """Small, borderless, always-on-top badge shown during the countdown.
    The whole point of the countdown existing at all is so the user has
    time to open the Cinnamon menu or arrange a window before the shot
    fires — a silent countdown with nothing on screen would defeat that,
    so this is deliberately visible even though the main app window is
    hidden for the same period."""

    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        self.set_default_size(110, 110)

        self.label = Gtk.Label(label="")
        self.label.set_name("cp-countdown-label")
        box = Gtk.Box()
        box.set_border_width(18)
        box.pack_start(self.label, True, True, 0)
        self.get_style_context().add_class("cp-countdown-box")
        self.add(box)

        css = Gtk.CssProvider()
        css.load_from_data(b"""
            .cp-countdown-box {
                background-color: rgba(0, 0, 0, 0.68);
                border-radius: 14px;
            }
            #cp-countdown-label {
                font-size: 42px;
                font-weight: bold;
                color: #ffffff;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def set_count(self, n):
        self.label.set_text(str(n))

    def place_top_right(self):
        screen = Gdk.Screen.get_default()
        self.move(max(0, screen.get_width() - 150), 40)


class _ScreenshotReviewDialog(Gtk.Dialog):
    """Shown immediately after a capture: a preview plus Retake/Keep.
    Nothing is written to disk until Keep is chosen — Retake just throws
    the just-captured pixbuf away and runs the countdown again.

    The mouse cursor is never baked into the base capture (see
    capture_screen_pixbuf) — if cursor_info is available, a checkbox
    here lets you composite it in for preview and for the final saved
    file, OFF by default. No cursor_info (system couldn't provide one) =
    no checkbox at all, and the base capture is used as-is."""

    RETAKE = 1
    KEEP = 2

    def __init__(self, parent, pixbuf, cursor_info=None):
        super().__init__(title="Keep This Screenshot?", transient_for=parent, flags=0)
        self.set_default_size(480, 340)
        self.set_resizable(False)

        self._base_pixbuf = pixbuf
        self._cursor_info = cursor_info
        self.show_cursor = False  # off by default — an arbitrary pointer

        box = self.get_content_area()
        box.set_border_width(10)
        box.set_spacing(8)

        self._image = Gtk.Image()
        frame = Gtk.Frame()
        frame.add(self._image)
        box.pack_start(frame, True, True, 0)

        if cursor_info is not None:
            cursor_check = Gtk.CheckButton(label="Show mouse cursor in screenshot")
            cursor_check.set_active(False)
            cursor_check.connect("toggled", self._on_cursor_toggled)
            box.pack_start(cursor_check, False, False, 0)

        hint = Gtk.Label(
            label="This is what gets saved with the preset.",
            xalign=0.5,
        )
        box.pack_start(hint, False, False, 0)

        self.add_button("Retake", self.RETAKE)
        self.add_button("Keep", self.KEEP)
        self.set_default_response(self.KEEP)

        self._refresh_preview()
        self.show_all()

    def _on_cursor_toggled(self, checkbutton):
        self.show_cursor = checkbutton.get_active()
        self._refresh_preview()

    def _refresh_preview(self):
        preview = _scale_pixbuf_to_fit(self.get_result_pixbuf(), 460, 240)
        self._image.set_from_pixbuf(preview)

    def get_result_pixbuf(self):
        """What Keep should actually save: the base capture, composited
        with the cursor glyph only if the checkbox is checked."""
        if self.show_cursor and self._cursor_info is not None:
            return composite_cursor_onto(
                self._base_pixbuf,
                self._cursor_info["pixbuf"],
                self._cursor_info["hotspot"],
                *self._cursor_info["position"],
            )
        return self._base_pixbuf


class ScreenshotCaptureFlow:
    """Orchestrates hide -> countdown -> capture -> keep/retake. Construct
    one per capture session and call .start(); on_finished(pixbuf_or_None)
    fires exactly once, when the user keeps a shot, cancels the review
    dialog, or capture itself fails — never mid-retake."""

    def __init__(self, parent_window, on_finished):
        self.parent = parent_window
        self.on_finished = on_finished
        self._overlay = None
        self._remaining = 0
        self._was_visible = True

    def start(self):
        GLib.idle_add(self._begin_countdown)

    def _begin_countdown(self):
        # Hide the app itself so it never appears in its own screenshot.
        # Always restored in _finish_countdown(), success or failure.
        self._was_visible = self.parent.get_visible()
        self.parent.hide()

        self._overlay = _CountdownOverlay()
        self._overlay.place_top_right()
        self._remaining = SCREENSHOT_COUNTDOWN_SECONDS
        self._overlay.set_count(self._remaining)
        self._overlay.show_all()

        GLib.timeout_add_seconds(1, self._tick)
        return False

    def _tick(self):
        self._remaining -= 1
        if self._remaining <= 0:
            self._finish_countdown()
            return False
        self._overlay.set_count(self._remaining)
        return True

    def _finish_countdown(self):
        if self._overlay is not None:
            self._overlay.destroy()
            self._overlay = None

        # destroy() only *schedules* the unmap — it doesn't block until the
        # X server/compositor has actually redrawn the screen without the
        # countdown badge on it. Capturing on the very next line was
        # grabbing a frame that still had the countdown baked in (visible
        # in testing: a screenshot with a "1" badge in the corner). Force
        # the pending unmap through, then give the compositor a brief
        # moment to actually repaint before the real capture happens.
        display = Gdk.Display.get_default()
        if display is not None:
            display.flush()
        while Gtk.events_pending():
            Gtk.main_iteration()

        GLib.timeout_add(150, self._do_capture)

    def _do_capture(self):
        pixbuf, error = None, None
        try:
            pixbuf = capture_screen_pixbuf()
        except Exception as e:
            error = str(e)

        cursor_info = None
        if not error:
            try:
                cursor_info = capture_cursor_overlay()
            except Exception:
                cursor_info = None  # best-effort only — never blocks the shot

        if self._was_visible:
            self.parent.show()

        if error:
            self._show_error(error)
        else:
            self._show_review(pixbuf, cursor_info)
        return False

    def _show_error(self, error):
        dialog = Gtk.MessageDialog(
            transient_for=self.parent, flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Couldn't capture the screen.",
        )
        dialog.format_secondary_text(error)
        dialog.run()
        dialog.destroy()
        self.on_finished(None)

    def _show_review(self, pixbuf, cursor_info):
        dialog = _ScreenshotReviewDialog(self.parent, pixbuf, cursor_info)
        response = dialog.run()
        result_pixbuf = dialog.get_result_pixbuf() if response == _ScreenshotReviewDialog.KEEP else None
        dialog.destroy()
        if response == _ScreenshotReviewDialog.RETAKE:
            self._begin_countdown()
        elif response == _ScreenshotReviewDialog.KEEP:
            self.on_finished(result_pixbuf)
        else:
            self.on_finished(None)


# ---------------------------------------------------------------------------
# GTK UI
# ---------------------------------------------------------------------------

def run_with_progress(parent, title, message, work_fn, on_done):
    """Roadmap addendum (retrofitted into Phase 4 Save and Phase 5 Apply,
    ahead of Phase 6 reusing it): runs work_fn() on a background thread
    instead of blocking the GTK main loop, showing a small indeterminate
    progress dialog in the meantime. Without this, bundling a large
    custom theme on Save, or Plymouth's initramfs rebuild on Apply, just
    freezes the window with zero feedback -- looks crashed, not busy.

    work_fn takes no arguments and either returns a result or raises.
    on_done(result, error) is called back on the GTK main thread once it
    finishes (via GLib.idle_add, the standard safe way to hand control
    back to the main loop from a worker thread) -- error is None on
    success, result is None on failure. Nothing work_fn calls may touch
    GTK/GDK objects directly, since it runs off the main thread; the
    functions this is used with (save_preset, apply_preset,
    apply_lightdm/plymouth/grub) are all pure filesystem/dconf/subprocess
    work already, so this holds without any changes to them.

    Deliberately has no Cancel button: none of what runs behind this (a
    dconf load already in flight, a pkexec call mid-authentication, a
    shutil.copytree partway through) is safe to interrupt, so this
    doesn't pretend otherwise. Phase 6's Import/Export explicitly calls
    for a *safe* cancel — that's a different, cancel-aware work_fn
    design, not something this dialog can retrofit on its own; it should
    still reuse this dialog for its progress display, just with a
    work_fn that actually checks a cancellation flag periodically."""
    dialog = Gtk.Dialog(title=title, transient_for=parent, flags=0)
    dialog.set_default_size(360, 120)
    dialog.set_resizable(False)
    dialog.set_deletable(False)  # no safe way to interrupt what's running behind it
    dialog.set_modal(True)

    box = dialog.get_content_area()
    box.set_border_width(16)
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.pack_start(vbox, True, True, 0)

    message_label = Gtk.Label(label=message, xalign=0)
    message_label.set_line_wrap(True)
    message_label.set_max_width_chars(55)
    vbox.pack_start(message_label, False, False, 0)

    progress_bar = Gtk.ProgressBar()
    vbox.pack_start(progress_bar, False, False, 0)

    dialog.show_all()

    def pulse():
        progress_bar.pulse()
        return True

    pulse_source = GLib.timeout_add(120, pulse)

    def worker():
        try:
            result = work_fn()
            error = None
        except Exception as e:
            result = None
            error = e

        def finish():
            GLib.source_remove(pulse_source)
            dialog.destroy()
            on_done(result, error)
            return False

        GLib.idle_add(finish)

    threading.Thread(target=worker, daemon=True).start()
    return dialog


def run_export_with_progress(parent, title, message, work_fn, on_done):
    """Phase 6's cancel-safe sibling to run_with_progress() above. That
    one deliberately has no Cancel button, because nothing it's used for
    (a dconf load, a pkexec call mid-authentication) is safe to
    interrupt partway through. Export is the opposite: it only ever
    reads from PRESETS_DIR and writes to a throwaway .part file, so
    interrupting it is always safe -- which is exactly why it gets its
    own dialog instead of a cancel button bolted onto the other one.

    work_fn(cancel_event, progress_cb) runs on a background thread:
    cancel_event is a threading.Event the Cancel button sets, which
    work_fn (via export_preset()) checks between every file; progress_cb
    (current, total) drives a real, determinate progress bar instead of
    run_with_progress()'s indeterminate pulse, since file-by-file
    iteration means a real total is always known up front.

    on_done(result, error, cancelled) is called back on the GTK main
    thread once work_fn returns/raises/is cancelled -- cancelled is True
    only when the person actually clicked Cancel, so callers can show a
    neutral "cancelled" message instead of treating it as a failure."""
    dialog = Gtk.Dialog(title=title, transient_for=parent, flags=0)
    dialog.set_default_size(380, 140)
    dialog.set_resizable(False)
    dialog.set_deletable(False)
    dialog.set_modal(True)

    box = dialog.get_content_area()
    box.set_border_width(16)
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.pack_start(vbox, True, True, 0)

    message_label = Gtk.Label(label=message, xalign=0)
    message_label.set_line_wrap(True)
    message_label.set_max_width_chars(55)
    vbox.pack_start(message_label, False, False, 0)

    progress_bar = Gtk.ProgressBar()
    progress_bar.set_show_text(True)
    progress_bar.set_text("Preparing…")
    progress_bar.set_fraction(0.0)
    vbox.pack_start(progress_bar, False, False, 0)

    button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    cancel_btn = Gtk.Button(label="Cancel")
    button_row.pack_end(cancel_btn, False, False, 0)
    vbox.pack_start(button_row, False, False, 0)

    dialog.show_all()

    cancel_event = threading.Event()
    state = {"cancelled": False}

    def on_cancel_clicked(_btn):
        state["cancelled"] = True
        cancel_event.set()
        cancel_btn.set_sensitive(False)
        message_label.set_label("Cancelling…")

    cancel_btn.connect("clicked", on_cancel_clicked)

    def progress_cb(current, total):
        def update():
            frac = (current / total) if total else 0.0
            progress_bar.set_fraction(frac)
            progress_bar.set_text(f"{current} / {total} files")
            return False

        GLib.idle_add(update)

    def worker():
        try:
            result = work_fn(cancel_event, progress_cb)
            error = None
        except Exception as e:
            result = None
            error = e

        def finish():
            dialog.destroy()
            on_done(result, error, state["cancelled"])
            return False

        GLib.idle_add(finish)

    threading.Thread(target=worker, daemon=True).start()
    return dialog


def show_message_dialog(parent, title, message, message_type=Gtk.MessageType.INFO):
    """Small shared helper so Apply/Export/(later) Import don't each grow
    their own copy-pasted result-dialog method."""
    dialog = Gtk.MessageDialog(
        transient_for=parent, flags=0, message_type=message_type,
        buttons=Gtk.ButtonsType.OK, text=title,
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


class SavePresetWizard(Gtk.Dialog):
    """Roadmap Phase 4: the mandatory Save flow. Screenshot and Name are
    required before Save becomes clickable; Description is optional;
    the same 12-category checklist Export/Apply will reuse later sits
    behind a collapsible "Customize the theme's parameters" section,
    everything checked by default -- saving is local and risk-free, so
    there's nothing to warn about here (unlike Export's opt-in boot items
    or Apply's root prompts).

    Not run via .run(): screenshot capture is its own hide/countdown/
    capture/review cycle driven by GLib timeouts, and keeping the dialog
    non-modal-run avoids any doubt about whether those callbacks fire
    correctly out of a nested main loop. The caller connects to the
    "response" signal instead and is responsible for destroying the
    dialog once it's done with it (a failed name-collision check, for
    instance, wants the wizard to stay open so the person can just retype
    the name rather than losing their screenshot/description and having
    to start over)."""

    def __init__(self, parent):
        super().__init__(title="Save Preset", transient_for=parent, flags=0)
        self.set_default_size(480, 640)
        self.set_border_width(0)

        self.result_pixbuf = None
        self._category_checks = {}

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.save_btn = self.add_button("Save", Gtk.ResponseType.OK)
        self.save_btn.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.get_content_area().pack_start(scroll, True, True, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_border_width(14)
        scroll.add(content)

        # --- Thumbnail (mandatory) ------------------------------------
        thumb_label = Gtk.Label(xalign=0)
        thumb_label.set_markup('<span foreground="#cc0000">*</span> <b>Thumbnail</b>')
        content.pack_start(thumb_label, False, False, 0)

        self.thumb_image = Gtk.Image()
        thumb_frame = Gtk.Frame()
        thumb_frame.set_shadow_type(Gtk.ShadowType.IN)
        thumb_frame.add(self.thumb_image)
        content.pack_start(thumb_frame, False, False, 0)
        self.thumb_image.set_from_pixbuf(render_gradient_placeholder("save-wizard", 420, 210))

        self.screenshot_btn = Gtk.Button(label="Take a Screenshot")
        self.screenshot_btn.connect("clicked", self.on_take_screenshot)
        content.pack_start(self.screenshot_btn, False, False, 0)

        # --- Name (mandatory) -------------------------------------------
        name_label = Gtk.Label(xalign=0)
        name_label.set_markup('<span foreground="#cc0000">*</span> <b>Name</b>')
        content.pack_start(name_label, False, False, 0)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Input Name here")
        self.name_entry.connect("changed", self._update_save_sensitivity)
        self.name_entry.set_activates_default(True)
        content.pack_start(self.name_entry, False, False, 0)

        # --- Description (optional) --------------------------------------
        desc_label = Gtk.Label(label="Description", xalign=0)
        content.pack_start(desc_label, False, False, 0)
        # BETA-0.10 fix: was a bare Gtk.ScrolledWindow(shadow_type=IN) --
        # that sunken border renders fine under Adwaita but is nearly
        # invisible under flatter/custom GTK themes, making the box look
        # like it isn't rendering at all. An explicit Frame (same pattern
        # already used for the thumbnail above) draws a border far more
        # consistently across themes.
        desc_frame = Gtk.Frame()
        desc_frame.set_shadow_type(Gtk.ShadowType.IN)
        content.pack_start(desc_frame, False, False, 0)
        desc_scroll = Gtk.ScrolledWindow()
        desc_scroll.set_min_content_height(70)
        desc_scroll.set_shadow_type(Gtk.ShadowType.NONE)  # the Frame above draws the border now
        self.description_view = Gtk.TextView()
        self.description_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.description_view.set_top_margin(6)
        self.description_view.set_left_margin(6)
        self.description_view.set_right_margin(6)
        desc_scroll.add(self.description_view)
        desc_frame.add(desc_scroll)

        # --- Collapsible per-category checklist, all checked by default -
        expander = Gtk.Expander(label="Customize the theme's parameters")
        content.pack_start(expander, False, False, 6)

        checklist_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        checklist_box.set_margin_top(10)
        expander.add(checklist_box)

        for cat in CATEGORY_ORDER:
            checklist_box.pack_start(self._build_category_row(cat), False, False, 0)

        self._update_save_sensitivity()
        self.show_all()

    def _build_category_row(self, cat):
        row, check = build_category_checklist_row(cat, 44, initial_checked=True)
        self._category_checks[cat] = check
        return row

    def on_take_screenshot(self, _btn):
        # ScreenshotCaptureFlow already hides/shows `self` (the wizard),
        # but the main window sitting behind it would otherwise still be
        # visible in the capture -- hide it too, independently, for the
        # same duration.
        main_window = self.get_transient_for()

        def on_finished(pixbuf):
            if main_window is not None:
                main_window.show()
            if pixbuf is None:
                return  # cancelled/failed -- leave whatever was there before untouched
            self.result_pixbuf = pixbuf
            self.thumb_image.set_from_pixbuf(_scale_pixbuf_to_fit(pixbuf, 420, 240))
            self.screenshot_btn.set_label("Retake Screenshot")
            self._update_save_sensitivity()

        if main_window is not None:
            main_window.hide()
        ScreenshotCaptureFlow(self, on_finished).start()

    def _update_save_sensitivity(self, *_args):
        has_name = bool(self.name_entry.get_text().strip())
        has_shot = self.result_pixbuf is not None
        self.save_btn.set_sensitive(has_name and has_shot)

    def get_name(self):
        return self.name_entry.get_text().strip()

    def get_description(self):
        buf = self.description_view.get_buffer()
        start, end = buf.get_bounds()
        return buf.get_text(start, end, False).strip()

    def get_selected_categories(self):
        return {cat: check.get_active() for cat, check in self._category_checks.items()}


class GrubCooldownDialog(Gtk.Dialog):
    """Roadmap Phase 7: GRUB is the one action in the app with a
    genuinely bad worst case (a broken boot menu), so it gets an extra
    layer beyond the plain Yes/No every other boot item uses -- a
    forced, non-privileged cooldown with a visible countdown, ending in
    a red Continue button that stays disabled until time's up. Nothing
    here touches the system or asks for root; it's purely "make sure a
    rushed click can't skip past this" before the real pkexec prompt
    (still shown afterward, same as every other boot item) becomes
    reachable at all.

    Run via .run() like the app's other short confirmation dialogs --
    GLib.timeout_add_seconds callbacks fire correctly inside a Dialog's
    nested main loop, same as the screenshot countdown already relies
    on elsewhere in this file."""

    COOLDOWN_SECONDS = 18

    def __init__(self, parent, preset_name):
        super().__init__(title="Apply GRUB Bootloader — Confirm", transient_for=parent, flags=0)
        self.set_default_size(400, 320)
        self.set_resizable(False)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.continue_btn = self.add_button(f"Continue ({self.COOLDOWN_SECONDS}s)", Gtk.ResponseType.OK)
        self.continue_btn.set_sensitive(False)
        # Can't accidentally Enter-key past the cooldown while Continue
        # is still disabled -- Cancel is the default response until the
        # timer hands it over.
        self.set_default_response(Gtk.ResponseType.CANCEL)

        box = self.get_content_area()
        box.set_border_width(16)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.pack_start(vbox, True, True, 0)

        warn_label = Gtk.Label(xalign=0)
        warn_label.set_line_wrap(True)
        warn_label.set_max_width_chars(48)
        warn_label.set_markup(
            '<span foreground="#cc0000"><b>⚠ This replaces your GRUB '
            "bootloader configuration and regenerates your boot menu "
            f"(update-grub) from '{GLib.markup_escape_text(preset_name)}'.</b></span>\n\n"
            "A broken GRUB config is the one mistake in this app that "
            "can genuinely affect whether your computer boots. A backup "
            "of your current config is made automatically before this "
            "runs, and can be restored from the GRUB section afterward "
            "if something goes wrong.\n\n"
            "Take a moment before continuing."
        )
        vbox.pack_start(warn_label, False, False, 0)

        self._seconds_left = self.COOLDOWN_SECONDS
        self._timeout_id = GLib.timeout_add_seconds(1, self._tick)
        self.connect("destroy", self._stop_timer)

        self.show_all()

    def _tick(self):
        self._seconds_left -= 1
        if self._seconds_left <= 0:
            self.continue_btn.set_label("Continue")
            self.continue_btn.set_sensitive(True)
            self.continue_btn.get_style_context().add_class("destructive-action")
            self.set_default_response(Gtk.ResponseType.OK)
            self._timeout_id = None
            return False
        self.continue_btn.set_label(f"Continue ({self._seconds_left}s)")
        return True

    def _stop_timer(self, *_args):
        # Dialog can be destroyed (Cancel, or the WM close button) before
        # the countdown finishes -- drop the still-pending timeout source
        # rather than let it fire against widgets that no longer exist.
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None


class ApplyPresetDialog(Gtk.Dialog):
    """Roadmap Phase 5: fully replaces the old separate SystemBootDialog.
    One scrollable page per preset, broken into independent, separately
    authorized sections: Apply Theme (no root, own "Customize the theme's
    parameters" sub-checklist so it's not all-or-nothing) plus Apply Lock
    Screen / Apply Boot Animation / Apply GRUB Bootloader, each root-gated
    with its own pkexec call — authorizing one boot-level section never
    grants access to the others."""

    BOOT_ITEMS = [
        ("lightdm", "Apply Lock Screen",
         "(Requires root) Replaces /etc/lightdm/slick-greeter.conf. A "
         "backup of the previous file is kept alongside it."),
        ("plymouth", "Apply Boot Animation",
         "(Requires root) Installs the theme (if needed) and rebuilds "
         "the initramfs. This can take a little while."),
        ("grub", "Apply GRUB Bootloader",
         "(Requires root) Replaces /etc/default/grub and runs "
         "update-grub. A backup of the previous file is kept alongside "
         "it. Double-check this is the preset you want — a bad GRUB "
         "config can affect booting."),
    ]

    # Items that haven't been verified end-to-end yet get a red warning
    # instead of being quietly presented as equally solid. Phase 7 added
    # GRUB's own cooldown timer (GrubCooldownDialog) and the "Restore
    # Previous Config" button below on top of this — but per the
    # roadmap's own explicit item, this flag only comes off after
    # independent real-hardware testing confirms the whole flow, not
    # just when the phase's other checklist items are built. Stays red
    # until then.
    UNTESTED = {
        "grub": "⚠ UNTESTED — not yet verified end-to-end. Use with caution "
                "and double-check your system boots correctly afterward.",
    }

    # BETA-0.17 (Roadmap Addendum: Backups, b-lite): "Restore Previous
    # Configuration" used to be GRUB-only; now all three boot items behave
    # consistently. Keyed the same as BOOT_ITEMS above.
    BACKUP_FUNCS = {
        "lightdm": (lightdm_backup_exists, restore_lightdm_backup),
        "plymouth": (plymouth_backup_exists, restore_plymouth_backup),
        "grub": (grub_backup_exists, restore_grub_backup),
    }

    def __init__(self, parent, preset_name):
        super().__init__(title=f"Apply Preset — {preset_name}", transient_for=parent, flags=0)
        self.preset_name = preset_name
        self.preset_dir = PRESETS_DIR / preset_name
        self.meta = load_meta(preset_name)
        self.set_default_size(480, 640)

        self._theme_checks = {}
        self._restore_btns = {}

        self.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.set_border_width(12)
        self.get_content_area().pack_start(outer, True, True, 0)

        outer.pack_start(build_dialog_title_header("Apply Preset", preset_name), False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        outer.pack_start(scroll, True, True, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(4)
        scroll.add(box)

        box.pack_start(self._build_theme_section(), False, False, 0)

        for key, title, description in self.BOOT_ITEMS:
            box.pack_start(self._build_boot_row(key, title, description), False, False, 0)

        # BUG FIX: this used to be box.show_all() -- showing the content
        # before the dialog's own top-level window is realized. GTK3 can
        # fail to queue the initial paint for content shown that way, even
        # though every widget correctly ends up with visible=True — the
        # dialog opens with real widgets in the tree, correct visibility
        # flags, correct size allocation, and a completely blank white
        # body regardless. Showing the whole dialog (top-level + content)
        # together in one self.show_all() call, instead of showing the
        # content separately and earlier, avoids the bad ordering.
        self._refresh_gtk_override_banner()
        self.show_all()

    # --- Apply Theme: no root, own per-category checklist ------------------

    def _build_theme_section(self):
        frame = Gtk.Frame()
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_border_width(10)
        frame.add(inner)

        title_label = Gtk.Label(xalign=0)
        title_label.set_markup("<b>Apply Theme</b>")
        inner.add(title_label)

        desc_label = Gtk.Label(
            xalign=0,
            label="Applies this preset's theme to your home directory. No "
                  "admin rights needed, and this never touches the login "
                  "screen, boot animation, or bootloader.",
        )
        desc_label.set_line_wrap(True)
        desc_label.set_max_width_chars(55)
        inner.add(desc_label)

        # Populated (or left empty) by _refresh_gtk_override_banner(),
        # called once below and again right after every Apply Theme run —
        # this file sits outside dconf and outside any preset's own
        # folder, so nothing here can clear it; the best this dialog can
        # do is keep telling the truth about whether it's still there.
        self.gtk_override_banner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        inner.add(self.gtk_override_banner)

        expander = Gtk.Expander(label="Customize the theme's parameters")
        inner.add(expander)
        checklist_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        checklist_box.set_margin_top(10)
        expander.add(checklist_box)
        for cat in THEME_CATEGORIES:
            checklist_box.pack_start(self._build_category_row(cat), False, False, 0)

        apply_btn = Gtk.Button(label="Apply Theme")
        apply_btn.get_style_context().add_class("suggested-action")
        apply_btn.connect("clicked", self._on_apply_theme)
        inner.add(apply_btn)

        # BETA-0.16 fix: this used to always take up a line of layout
        # space even when empty (its default state until an Apply
        # actually runs), showing as a dead gap between the button and
        # the frame's bottom edge. Hidden until there's real text to show.
        self.theme_status_label = Gtk.Label(label="", xalign=0)
        self.theme_status_label.set_line_wrap(True)
        self.theme_status_label.set_max_width_chars(55)
        self.theme_status_label.set_no_show_all(True)
        self.theme_status_label.hide()
        inner.add(self.theme_status_label)

        return frame

    def _build_category_row(self, cat):
        status = (self.meta.get("categories") or {}).get(cat)
        note = None
        if status == "skipped_on_purpose":
            note = "not saved"
        elif status in ("not_applicable", "not_implemented"):
            note = "nothing to apply"

        # A category this preset never captured (skipped at save time, or
        # never applicable) can't do anything useful when applied anyway
        # — pre-uncheck it rather than let the button silently no-op, but
        # leave it toggleable in case that status is wrong or changes.
        initial_checked = status not in ("skipped_on_purpose", "not_applicable", "not_implemented")

        row, check = build_category_checklist_row(cat, 40, initial_checked, status_note=note)
        self._theme_checks[cat] = check
        return row

    def _on_apply_theme(self, _btn):
        selected = {cat: check.get_active() for cat, check in self._theme_checks.items()}

        def work():
            return apply_preset(self.preset_name, selected)

        def on_done(result, error):
            self.theme_status_label.show()
            if error is not None:
                self.theme_status_label.set_markup(
                    f'<span foreground="#cc0000">Error: {GLib.markup_escape_text(str(error))}</span>'
                )
                self._refresh_gtk_override_banner()
                return

            warnings = result.get("warnings", [])
            errors = result.get("errors", [])
            if errors:
                text = "Applied, but some parts couldn't be applied:\n- " + "\n- ".join(errors)
                if warnings:
                    text += "\n\nAlso not found on this system:\n- " + "\n- ".join(warnings)
                self.theme_status_label.set_markup(
                    f'<span foreground="#cc0000">{GLib.markup_escape_text(text)}</span>'
                )
            elif warnings:
                self.theme_status_label.set_text(
                    "Applied. Cinnamon is reloading. Not found on this system:\n- "
                    + "\n- ".join(warnings)
                )
            else:
                self.theme_status_label.set_text("Applied. Cinnamon is reloading…")

            # What's on disk may have just changed (a theme swap can leave
            # a stray gtk.css behind or reveal one that was already masked
            # by a matching color) — re-check rather than trust the
            # pre-apply scan.
            self._refresh_gtk_override_banner()

        run_with_progress(self, "Applying Theme", "Applying theme…", work, on_done)

    def _refresh_gtk_override_banner(self):
        for child in list(self.gtk_override_banner.get_children()):
            self.gtk_override_banner.remove(child)

        strays = find_stray_gtk_overrides()
        if not strays:
            return

        names = ", ".join(p.name for p in strays)
        warn_label = Gtk.Label(xalign=0)
        warn_label.set_line_wrap(True)
        warn_label.set_max_width_chars(55)
        warn_label.set_markup(
            '<span foreground="#cc0000"><b>⚠ Found a GTK override outside this '
            "app's control</b></span>\n"
            f'<span foreground="#cc0000">{GLib.markup_escape_text(names)} in '
            "~/.config/ overrides parts of your theme on top of whatever "
            "preset is applied — if things look wrong after applying, "
            "this is likely why. No preset switch can ever clear it on "
            "its own.</span>"
        )
        self.gtk_override_banner.pack_start(warn_label, False, False, 0)

        delete_btn = Gtk.Button(label="Delete Override File(s)…")
        delete_btn.connect("clicked", self._on_delete_gtk_overrides, strays)
        self.gtk_override_banner.pack_start(delete_btn, False, False, 0)
        self.gtk_override_banner.show_all()

    def _on_delete_gtk_overrides(self, _btn, strays):
        confirm = Gtk.MessageDialog(
            transient_for=self, flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Delete these GTK override files?",
        )
        confirm.format_secondary_text(
            "\n".join(str(p) for p in strays)
            + "\n\nThis can't be undone. Only delete these if you don't "
              "recognize setting them yourself — they override theme "
              "colors/styles on top of anything this app applies."
        )
        response = confirm.run()
        confirm.destroy()
        if response != Gtk.ResponseType.YES:
            return

        errors = []
        for p in strays:
            try:
                p.unlink()
            except OSError as e:
                errors.append(f"{p}: {e}")

        self._refresh_gtk_override_banner()
        if errors:
            self._result_dialog("Some Files Couldn't Be Deleted", "\n".join(errors))

    # --- Lock Screen / Boot Animation / GRUB: each its own root prompt ----

    def _status_text(self, key):
        if key == "lightdm":
            info = self.meta.get("lightdm") or {}
            if info.get("status") == "saved":
                bits = []
                if info.get("background_file"):
                    bits.append("background image bundled")
                elif info.get("background_status") == "missing":
                    bits.append("background image was already gone at save time")
                elif info.get("background_status", "").startswith("unreadable"):
                    bits.append("background image couldn't be read")

                bundled_assets = [
                    kind for kind, asset in (info.get("assets") or {}).items()
                    if asset.get("status") == "bundled"
                ]
                if bundled_assets:
                    kind_labels = {"gtk": "style", "icon": "icon", "cursor": "cursor"}
                    names = sorted(kind_labels.get(k, k) for k in bundled_assets)
                    bits.append(f"custom {', '.join(names)} theme bundled")

                if bits:
                    return "Saved (" + "; ".join(bits) + ")."
                return "Saved (nothing custom to bundle — stock theme, solid color/no background)."
            if info.get("status") == "skipped_on_purpose":
                return "Not saved — unchecked at save time."
            if info.get("status") == "error":
                return f"Couldn't save: {info.get('error', 'unknown error')}"
            return "Not saved in this preset."
        if key == "plymouth":
            info = self.meta.get("plymouth") or {}
            theme = info.get("theme")
            if theme:
                bundled = " (bundled)" if info.get("status") == "bundled" else " (system theme)"
                return f"Theme: {theme}{bundled}"
            if info.get("status") == "skipped_on_purpose":
                return "Not saved — unchecked at save time."
            if info.get("status") == "error":
                return f"Couldn't save: {info.get('error', 'unknown error')}"
            return "Not saved in this preset."
        if key == "grub":
            info = self.meta.get("grub") or {}
            if info.get("status") == "saved":
                theme = info.get("theme")
                return f"Saved.{' Theme: ' + theme if theme else ''}"
            if info.get("status") == "skipped_on_purpose":
                return "Not saved — unchecked at save time."
            if info.get("status") == "error":
                return f"Couldn't save: {info.get('error', 'unknown error')}"
            return "Not saved in this preset."
        return ""

    def _build_boot_row(self, key, title, description):
        frame = Gtk.Frame()
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner.set_border_width(8)
        frame.add(inner)

        title_label = Gtk.Label(label=f"<b>{title}</b>", use_markup=True, xalign=0)
        inner.add(title_label)

        # "(Requires root)" is always the literal leading prefix of every
        # BOOT_ITEMS description (see the class-level list above) --
        # split it out so it can be marked up in red while the rest of
        # the sentence stays plain text, rather than reddening the whole
        # description.
        root_prefix = "(Requires root) "
        if description.startswith(root_prefix):
            rest = description[len(root_prefix):]
            desc_markup = (
                '<span foreground="#cc0000" weight="bold">(Requires root)</span> '
                + GLib.markup_escape_text(rest)
            )
        else:
            desc_markup = GLib.markup_escape_text(description)
        desc_label = Gtk.Label(xalign=0)
        desc_label.set_markup(desc_markup)
        desc_label.set_line_wrap(True)
        desc_label.set_max_width_chars(50)
        inner.add(desc_label)

        warning = self.UNTESTED.get(key)
        if warning:
            warn_label = Gtk.Label(
                label=f'<span foreground="#cc0000"><b>{GLib.markup_escape_text(warning)}</b></span>',
                use_markup=True, xalign=0,
            )
            warn_label.set_line_wrap(True)
            warn_label.set_max_width_chars(50)
            inner.add(warn_label)

        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_label = Gtk.Label(label=self._status_text(key), xalign=0)
        status_label.set_line_wrap(True)
        status_label.set_max_width_chars(40)
        row_box.pack_start(status_label, True, True, 0)

        if key in self.BACKUP_FUNCS:
            # Undoes this app's own most recent apply for this item,
            # regardless of which preset that was — visible only when a
            # backup actually exists, refreshed after every apply/restore
            # rather than only computed once here.
            backup_exists_fn, _ = self.BACKUP_FUNCS[key]
            restore_btn = Gtk.Button(label="Restore Previous Config")
            restore_btn.connect("clicked", self._on_restore_boot_item, key, title)
            restore_btn.set_visible(backup_exists_fn())
            self._restore_btns[key] = restore_btn
            row_box.pack_start(restore_btn, False, False, 0)

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.get_style_context().add_class("suggested-action")
        apply_btn.connect("clicked", self._on_apply_boot_item, key, title)
        row_box.pack_start(apply_btn, False, False, 0)
        inner.add(row_box)

        return frame

    def _on_apply_boot_item(self, _btn, key, title):
        if key == "grub":
            # Phase 7: GRUB gets the extra non-privileged cooldown step
            # instead of the plain Yes/No every other boot item uses —
            # see GrubCooldownDialog's own docstring for why.
            cooldown = GrubCooldownDialog(self, self.preset_name)
            response = cooldown.run()
            cooldown.destroy()
            if response != Gtk.ResponseType.OK:
                return
        else:
            confirm = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"{title} from '{self.preset_name}'?",
            )
            confirm.format_secondary_text(
                "This needs admin rights and will ask you to authenticate. "
                "Authorizing this never grants access to any other item here."
            )
            response = confirm.run()
            confirm.destroy()
            if response != Gtk.ResponseType.YES:
                return

        def work():
            if key == "lightdm":
                return apply_lightdm(self.preset_dir, self.meta)
            elif key == "plymouth":
                # No config file to snapshot for Plymouth (see
                # restore_plymouth_backup()'s docstring) -- record
                # whatever's currently active right before changing it,
                # so there's something for Restore to undo back to.
                _record_plymouth_previous_theme()
                return apply_plymouth(self.preset_dir, self.meta)
            elif key == "grub":
                return apply_grub(self.preset_dir, self.meta)
            return None

        def on_done(result, error):
            if error is not None:
                self._result_dialog(f"{title} — Failed", str(error))
            else:
                self._result_dialog(f"{title} — Done", result or "Applied.")
            self._refresh_restore_button(key)

        # Plymouth's is the one case here that can genuinely take a
        # while (rebuilding the initramfs, not just the pkexec prompt
        # itself) -- called out specifically so it doesn't look hung.
        progress_message = (
            "Rebuilding the boot image — this can take a little while…"
            if key == "plymouth"
            else "Applying — waiting on admin authentication if needed…"
        )
        run_with_progress(self, title, progress_message, work, on_done)

    RESTORE_CONFIRM_TEXT = {
        "grub": (
            "Reverts /etc/default/grub to what it was before this app's "
            "last GRUB apply, and regenerates the boot menu. Needs admin "
            "rights. This undoes the app's own last change, not "
            "something from a specific preset, so it isn't gated behind "
            "the same cooldown as applying a new config."
        ),
        "lightdm": (
            "Reverts the LightDM greeter config to what it was before "
            "this app's last apply. Needs admin rights. This undoes the "
            "app's own last change, not something from a specific "
            "preset."
        ),
        "plymouth": (
            "Switches back to whichever Plymouth theme was active right "
            "before this app's last Boot Animation apply, and rebuilds "
            "the boot image. Needs admin rights, and can take a little "
            "while for the same reason applying one does."
        ),
    }

    def _on_restore_boot_item(self, _btn, key, title):
        confirm = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Restore the previous {title.replace('Apply ', '')} configuration?",
        )
        confirm.format_secondary_text(self.RESTORE_CONFIRM_TEXT.get(key, ""))
        response = confirm.run()
        confirm.destroy()
        if response != Gtk.ResponseType.YES:
            return

        _, restore_fn = self.BACKUP_FUNCS[key]

        def work():
            return restore_fn()

        def on_done(result, error):
            if error is not None:
                self._result_dialog("Restore Failed", str(error))
            else:
                self._result_dialog("Restore Done", result or "Restored.")
            self._refresh_restore_button(key)

        progress_message = (
            "Rebuilding the boot image — this can take a little while…"
            if key == "plymouth"
            else "Restoring — waiting on admin authentication if needed…"
        )
        run_with_progress(self, "Restoring Previous Configuration", progress_message, work, on_done)

    def _refresh_restore_button(self, key):
        btn = self._restore_btns.get(key)
        if btn is not None:
            backup_exists_fn, _ = self.BACKUP_FUNCS[key]
            btn.set_visible(backup_exists_fn())

    def _result_dialog(self, title, message):
        show_message_dialog(self, title, message)


class ExportDialog(Gtk.Dialog):
    """Phase 6 (part 1). Same visual grammar as Save/Apply's checklist —
    same icons, same labels, same descriptions, via the same
    build_category_checklist_row() — but a different default checkbox
    state, which is deliberate and is the entire point of repeating this
    UI a third time rather than just reusing SavePresetWizard's: saving
    is local and risk-free (everything checked), applying is gated by
    root regardless of anything else (the auth prompt is the safety
    net), but exporting leaves the machine — so the three boot-level,
    root-requiring categories (Lock Screen / Boot Animation / GRUB)
    start unchecked here and must be deliberately opted into, while
    everything else defaults to whatever this preset actually has
    (pre-unchecked, with a dim note, if there's nothing there to send).

    Assumes the preset already has a screenshot — the caller is
    responsible for checking that before ever constructing this, since
    "no screenshot" should stop the flow before the person spends time
    picking categories, not after. export_preset() re-checks it anyway,
    since this dialog isn't the only path that could call it."""

    def __init__(self, parent, preset_name, meta):
        super().__init__(title=f"Export '{preset_name}'", transient_for=parent, flags=0)
        self.set_default_size(480, 640)
        self.preset_name = preset_name
        self.meta = meta
        self._category_checks = {}

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.export_btn = self.add_button("Export…", Gtk.ResponseType.OK)
        self.export_btn.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)
        self.connect("response", self._on_response)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_border_width(14)
        self.get_content_area().pack_start(outer, True, True, 0)

        outer.pack_start(build_dialog_title_header("Export Preset", preset_name), False, False, 0)

        intro = Gtk.Label(xalign=0)
        intro.set_line_wrap(True)
        intro.set_max_width_chars(65)
        intro.set_markup(
            "Choose what to include in the exported file. "
            "<b>Lock Screen, Boot Animation, and GRUB Bootloader are left "
            "unchecked by default</b> since they leave this machine — "
            "check any of them on purpose if you want them included."
        )
        outer.pack_start(intro, False, False, 0)

        # Framed like a distinct panel rather than a flat, unbordered list —
        # matches the "Apply" screen's section framing instead of standing
        # out as the one checklist screen without any visual boundary.
        panel_frame = Gtk.Frame()
        panel_frame.set_shadow_type(Gtk.ShadowType.IN)
        outer.pack_start(panel_frame, True, True, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        panel_frame.add(scroll)

        checklist_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        checklist_box.set_border_width(12)
        scroll.add(checklist_box)

        statuses = meta.get("categories") or {}
        for cat in CATEGORY_ORDER:
            checklist_box.pack_start(self._build_category_row(cat, statuses.get(cat)), False, False, 0)

        self.show_all()

    ROOT_EXPORT_CATEGORIES = ("lightdm", "plymouth", "grub")

    def _build_category_row(self, cat, status):
        note = None
        if status == "skipped_on_purpose":
            note = "not saved"
        elif status in ("not_applicable", "not_implemented"):
            note = "nothing to export"

        if cat in self.ROOT_EXPORT_CATEGORIES:
            initial_checked = False  # opt-in only — export leaves the machine
        else:
            initial_checked = status not in ("skipped_on_purpose", "not_applicable", "not_implemented")

        row, check = build_category_checklist_row(cat, 44, initial_checked, status_note=note)
        self._category_checks[cat] = check
        return row

    def get_selected_categories(self):
        return {cat: check.get_active() for cat, check in self._category_checks.items()}

    def _on_response(self, _dialog, response_id):
        if response_id != Gtk.ResponseType.OK:
            self.destroy()
            return

        chooser = Gtk.FileChooserDialog(
            title="Export Preset As",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        chooser.set_default_size(720, 520)
        chooser.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "Save", Gtk.ResponseType.OK,
        )
        chooser.set_do_overwrite_confirmation(True)
        chooser.set_current_name(f"{self.preset_name}.tar.gz")
        filt = Gtk.FileFilter()
        filt.set_name("Cinnamon Presets archive (*.tar.gz)")
        filt.add_pattern("*.tar.gz")
        chooser.add_filter(filt)

        chooser_response = chooser.run()
        dest_path = chooser.get_filename() if chooser_response == Gtk.ResponseType.OK else None
        chooser.destroy()
        if not dest_path:
            return  # stay open — this was the file-picker's own Cancel, not the whole export

        if not dest_path.endswith(".tar.gz"):
            dest_path += ".tar.gz"

        selected = self.get_selected_categories()

        def work(cancel_event, progress_cb):
            return export_preset(self.preset_name, dest_path, selected, cancel_event, progress_cb)

        def on_done(result, error, cancelled):
            if cancelled:
                show_message_dialog(self, "Export Cancelled", "No file was written.")
            elif error is not None:
                show_message_dialog(self, "Export Failed", str(error), Gtk.MessageType.ERROR)
            else:
                show_message_dialog(self, "Export Complete", f"Saved to:\n{result}")
                self.destroy()

        run_export_with_progress(
            self, "Exporting Preset", f"Exporting '{self.preset_name}'…", work, on_done,
        )


class ImportPreviewDialog(Gtk.Dialog):
    """Shown after picking a file, before extraction -- same centered
    title/name header and the same category-row visual language as
    Export, but read-only: an import brings in whatever the archive
    actually contains, there's no picking a subset here (that choice
    already happened when the archive was exported). Lets someone see
    what they're about to import instead of finding out only after
    it's already sitting in their preset list."""

    def __init__(self, parent, preset_name, archive_meta):
        super().__init__(title=f"Import '{preset_name}'", transient_for=parent, flags=0)
        self.set_default_size(480, 640)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.import_btn = self.add_button("Import", Gtk.ResponseType.OK)
        self.import_btn.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_border_width(14)
        self.get_content_area().pack_start(outer, True, True, 0)

        outer.pack_start(build_dialog_title_header("Import Preset", preset_name), False, False, 0)

        intro = Gtk.Label(xalign=0)
        intro.set_line_wrap(True)
        intro.set_max_width_chars(65)
        intro.set_markup(
            "This is what the archive contains. Importing adds it to your "
            "preset list only — nothing is applied to your desktop until "
            "you choose to Apply it afterward."
        )
        outer.pack_start(intro, False, False, 0)

        panel_frame = Gtk.Frame()
        panel_frame.set_shadow_type(Gtk.ShadowType.IN)
        outer.pack_start(panel_frame, True, True, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        panel_frame.add(scroll)

        checklist_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        checklist_box.set_border_width(12)
        scroll.add(checklist_box)

        statuses = (archive_meta or {}).get("categories") or {}
        for cat in CATEGORY_ORDER:
            status = statuses.get(cat)
            present = status not in ("skipped_on_purpose", "not_applicable", "not_implemented", None)
            note = "included" if present else "not in this archive"
            row, check = build_category_checklist_row(cat, 40, present, status_note=note)
            check.set_sensitive(False)  # informational only -- see class docstring
            checklist_box.pack_start(row, False, False, 0)

        self.show_all()


class DiskUsageBar(Gtk.DrawingArea):
    """Three quantities summing to a total (this app's usage / rest of
    the system / free space) — GtkLevelBar is a single-value gauge, not
    this, and GTK has no built-in widget for a stacked proportional bar,
    so this is a small custom Cairo draw on a DrawingArea instead."""

    def __init__(self):
        super().__init__()
        self.set_size_request(-1, 22)
        self.app_bytes = 0
        self.other_bytes = 0
        self.free_bytes = 0
        self.connect("draw", self._on_draw)

    def set_values(self, app_bytes, other_bytes, free_bytes):
        self.app_bytes = max(0, app_bytes)
        self.other_bytes = max(0, other_bytes)
        self.free_bytes = max(0, free_bytes)
        self.queue_draw()

    def _on_draw(self, widget, ctx):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        total = self.app_bytes + self.other_bytes + self.free_bytes
        radius = min(6, height / 2)

        # Rounded-rect clip so all three segments share one soft outline
        # instead of each drawing its own corners.
        ctx.new_sub_path()
        ctx.arc(radius, radius, radius, 3.14159, 3 * 3.14159 / 2)
        ctx.arc(width - radius, radius, radius, 3 * 3.14159 / 2, 0)
        ctx.arc(width - radius, height - radius, radius, 0, 3.14159 / 2)
        ctx.arc(radius, height - radius, radius, 3.14159 / 2, 3.14159)
        ctx.close_path()
        ctx.clip()

        if total <= 0:
            ctx.set_source_rgb(0.85, 0.85, 0.85)
            ctx.paint()
            return

        segments = [
            (self.other_bytes, (0.35, 0.35, 0.38)),   # dark: rest of the system
            (self.app_bytes, (0.20, 0.55, 0.85)),     # vibrant: this app
            (self.free_bytes, (0.90, 0.90, 0.90)),    # light gray: free
        ]
        x = 0.0
        for amount, (r, g, b) in segments:
            seg_width = width * (amount / total)
            ctx.set_source_rgb(r, g, b)
            ctx.rectangle(x, 0, seg_width, height)
            ctx.fill()
            x += seg_width


class SettingsWindow(Gtk.Dialog):
    """Roadmap Phase 9 (Settings Tab addendum). Gtk.Stack + Gtk.StackSidebar
    — matches Cinnamon Settings' own layout convention, scales better than
    one long scrolling page. Six sections: General, Diagnostics, Storage,
    Backups, Updates, About, in that fixed order."""

    def __init__(self, parent):
        super().__init__(title="Settings", transient_for=parent, flags=0)
        self.main_window = parent
        self.set_default_size(680, 520)
        self.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.get_content_area().pack_start(hbox, True, True, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(self.stack)
        hbox.pack_start(sidebar, False, False, 0)
        hbox.pack_start(self.stack, True, True, 0)

        self.stack.add_titled(self._build_general_page(), "general", "General")
        self.stack.add_titled(self._build_diagnostics_page(), "diagnostics", "Diagnostics")
        self.stack.add_titled(self._build_storage_page(), "storage", "Storage")
        self.stack.add_titled(self._build_backups_page(), "backups", "Backups")
        self.stack.add_titled(self._build_updates_page(), "updates", "Updates")
        self.stack.add_titled(self._build_about_page(), "about", "About")

        self.show_all()
        self._refresh_storage_page()

    def _scrolled_page(self, spacing=12):
        scroll = Gtk.ScrolledWindow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
        box.set_border_width(16)
        scroll.add(box)
        return scroll, box

    def _section_label(self, text):
        label = Gtk.Label(xalign=0)
        label.set_markup(f"<b>{GLib.markup_escape_text(text)}</b>")
        return label

    # --- General -------------------------------------------------------

    def _build_general_page(self):
        scroll, box = self._scrolled_page()
        settings = load_app_settings()

        box.pack_start(self._section_label("Default view when the app opens"), False, False, 0)
        view_combo = Gtk.ComboBoxText()
        view_combo.append("grid", "Grid")
        view_combo.append("list", "List")
        view_combo.set_active_id(settings["default_view_mode"])
        view_combo.connect("changed", self._on_general_changed, "default_view_mode")
        box.pack_start(view_combo, False, False, 0)

        box.pack_start(self._section_label("Default thumbnail size (grid view)"), False, False, 0)
        size_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL,
            CinnamonPresetsWindow.GRID_MIN_THUMB, CinnamonPresetsWindow.GRID_MAX_THUMB, 10,
        )
        size_scale.set_value(settings["default_thumb_size"])
        size_scale.set_draw_value(False)
        size_scale.connect("value-changed", self._on_general_thumb_size_changed)
        box.pack_start(size_scale, False, False, 0)

        box.pack_start(self._section_label("Default sort order"), False, False, 0)
        sort_combo = Gtk.ComboBoxText()
        sort_combo.append("name", "Name")
        sort_combo.append("date", "Date Saved")
        sort_combo.set_active_id(settings["default_sort_mode"])
        sort_combo.connect("changed", self._on_general_changed, "default_sort_mode")
        box.pack_start(sort_combo, False, False, 0)

        note = Gtk.Label(
            xalign=0,
            label="Changes here apply the next time the main window opens.",
        )
        note.get_style_context().add_class("dim-label")
        box.pack_start(note, False, False, 0)

        return scroll

    def _on_general_changed(self, combo, key):
        settings = load_app_settings()
        settings[key] = combo.get_active_id()
        save_app_settings(settings)

    def _on_general_thumb_size_changed(self, scale):
        settings = load_app_settings()
        settings["default_thumb_size"] = int(scale.get_value())
        save_app_settings(settings)

    # --- Diagnostics -----------------------------------------------------

    def _build_diagnostics_page(self):
        scroll, box = self._scrolled_page()

        box.pack_start(self._section_label("Stray GTK overrides"), False, False, 0)
        self.diag_gtk_label = Gtk.Label(xalign=0)
        self.diag_gtk_label.set_line_wrap(True)
        box.pack_start(self.diag_gtk_label, False, False, 0)
        self._refresh_diag_gtk_label()

        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        box.pack_start(self._section_label("Log file"), False, False, 0)
        log_path_label = Gtk.Label(label=str(LOG_FILE), xalign=0)
        log_path_label.set_selectable(True)
        log_path_label.get_style_context().add_class("dim-label")
        box.pack_start(log_path_label, False, False, 0)

        log_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.pack_start(log_btn_box, False, False, 0)

        open_log_btn = Gtk.Button(label="Open Log File")
        open_log_btn.connect("clicked", self._on_open_log_file)
        log_btn_box.pack_start(open_log_btn, False, False, 0)

        copy_diag_btn = Gtk.Button(label="Copy Diagnostic Info")
        copy_diag_btn.connect("clicked", self._on_copy_diagnostic_info)
        log_btn_box.pack_start(copy_diag_btn, False, False, 0)

        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        box.pack_start(self._section_label("Preset migration"), False, False, 0)
        migrate_note = Gtk.Label(
            xalign=0,
            label="Presets are upgraded to the current format automatically "
                  "on startup. Use this if one seems stuck on an older format.",
        )
        migrate_note.set_line_wrap(True)
        box.pack_start(migrate_note, False, False, 0)
        rerun_btn = Gtk.Button(label="Re-run Migration Now")
        rerun_btn.connect("clicked", self._on_rerun_migration)
        rerun_btn.set_halign(Gtk.Align.START)
        box.pack_start(rerun_btn, False, False, 0)

        return scroll

    def _refresh_diag_gtk_label(self):
        strays = find_stray_gtk_overrides()
        if strays:
            names = "\n".join(str(p) for p in strays)
            self.diag_gtk_label.set_markup(
                f'<span foreground="#cc0000">Found:</span>\n{GLib.markup_escape_text(names)}'
            )
        else:
            self.diag_gtk_label.set_text("None found.")

    def _on_open_log_file(self, _btn):
        try:
            if LOG_FILE.is_file():
                subprocess.Popen(["xdg-open", str(LOG_FILE)])
            else:
                show_message_dialog(self, "No Log File Yet", "Nothing has been logged yet.")
        except OSError as e:
            show_message_dialog(self, "Couldn't Open Log File", str(e))

    def _on_copy_diagnostic_info(self, _btn):
        text = get_diagnostic_info()
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()
        show_message_dialog(self, "Copied", "Diagnostic info copied to the clipboard.")

    def _on_rerun_migration(self, _btn):
        results = migrate_all_presets()
        changed = [name for name, result in results.items() if result is True]
        errors = {name: result for name, result in results.items() if isinstance(result, str)}
        lines = [f"Checked {len(results)} preset(s)."]
        if changed:
            lines.append(f"Upgraded: {', '.join(changed)}")
        if errors:
            lines.append("Errors:")
            lines.extend(f"  {name}: {msg}" for name, msg in errors.items())
        if not changed and not errors:
            lines.append("Everything was already current.")
        show_message_dialog(self, "Migration Complete", "\n".join(lines))
        if self.main_window is not None:
            self.main_window.refresh_list()

    # --- Storage -----------------------------------------------------------

    def _build_storage_page(self):
        scroll, box = self._scrolled_page()

        self.storage_warning_label = Gtk.Label(xalign=0)
        self.storage_warning_label.set_line_wrap(True)
        self.storage_warning_label.set_no_show_all(True)
        box.pack_start(self.storage_warning_label, False, False, 0)

        self.storage_big_label = Gtk.Label(xalign=0)
        box.pack_start(self.storage_big_label, False, False, 0)

        self.storage_detail_label = Gtk.Label(xalign=0)
        self.storage_detail_label.get_style_context().add_class("dim-label")
        box.pack_start(self.storage_detail_label, False, False, 0)

        self.disk_bar = DiskUsageBar()
        box.pack_start(self.disk_bar, False, False, 4)

        legend = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        for swatch_rgb, label_text in (
            ("#595961", "Rest of system"),
            ("#3389d9", "This app"),
            ("#e6e6e6", "Free"),
        ):
            item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            swatch = Gtk.DrawingArea()
            swatch.set_size_request(12, 12)
            color = Gdk.RGBA()
            color.parse(swatch_rgb)
            swatch.connect("draw", lambda w, c, col=color: (
                c.set_source_rgba(col.red, col.green, col.blue, 1.0),
                c.rectangle(0, 0, w.get_allocated_width(), w.get_allocated_height()),
                c.fill(),
            ))
            item.pack_start(swatch, False, False, 0)
            item.pack_start(Gtk.Label(label=label_text), False, False, 0)
            legend.pack_start(item, False, False, 0)
        box.pack_start(legend, False, False, 0)

        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        open_folder_btn = Gtk.Button(label="Open Presets Folder")
        open_folder_btn.set_halign(Gtk.Align.START)
        open_folder_btn.connect("clicked", self._on_open_presets_folder)
        box.pack_start(open_folder_btn, False, False, 0)

        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        danger_label = Gtk.Label(xalign=0)
        danger_label.set_markup('<span foreground="#8b0000"><b>Danger Zone</b></span>')
        box.pack_start(danger_label, False, False, 0)

        erase_btn = Gtk.Button(label="Erase All Data")
        erase_btn.get_style_context().add_class("destructive-action")
        erase_btn.set_halign(Gtk.Align.START)
        erase_btn.connect("clicked", self._on_erase_all_data)
        box.pack_start(erase_btn, False, False, 0)

        uninstall_btn = Gtk.Button(label="Uninstall…")
        uninstall_btn.get_style_context().add_class("destructive-action")
        uninstall_btn.set_halign(Gtk.Align.START)
        uninstall_btn.connect("clicked", self._on_uninstall)
        box.pack_start(uninstall_btn, False, False, 0)

        return scroll

    def _refresh_storage_page(self):
        info = get_storage_info()
        low = is_low_space(info["free"], info["total"])
        self.storage_warning_label.set_visible(low)
        if low:
            self.storage_warning_label.set_markup(
                '<span foreground="#cc0000"><b>⚠ Running low on disk space — '
                "consider freeing some up.</b></span>"
            )

        self.storage_big_label.set_markup(
            f"<span size='xx-large'><b>{format_bytes(info['app_bytes'])}</b></span>"
        )
        pct = (info["app_bytes"] / info["total"] * 100) if info["total"] else 0
        self.storage_detail_label.set_text(
            f"{pct:.2f}% of {format_bytes(info['total'])} on {info['mount_point']}"
        )
        self.disk_bar.set_values(info["app_bytes"], info["other_used"], info["free"])

    def _on_open_presets_folder(self, _btn):
        try:
            ensure_dirs()
            subprocess.Popen(["xdg-open", str(PRESETS_DIR)])
        except OSError as e:
            show_message_dialog(self, "Couldn't Open Folder", str(e))

    def _on_erase_all_data(self, _btn):
        confirm = Gtk.MessageDialog(
            transient_for=self, flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Erase all Cinnamon Presets data?",
        )
        confirm.format_secondary_text(
            f"Deletes {CONFIG_DIR} — every saved preset, this app's "
            "settings, and its logs. The app itself stays installed. "
            "This can't be undone."
        )
        # "Export Presets First" stays plain/regular — it's the safe,
        # non-destructive option, so it shouldn't compete visually with
        # the actual destructive action.
        confirm.add_button("Export Presets First", Gtk.ResponseType.HELP)
        confirm.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        erase_btn = confirm.add_button("Erase All Data", Gtk.ResponseType.OK)
        erase_btn.get_style_context().add_class("destructive-action")
        confirm.show_all()
        response = confirm.run()
        confirm.destroy()

        if response == Gtk.ResponseType.HELP:
            if self.main_window is not None:
                self.main_window.on_export(None)
            return
        if response != Gtk.ResponseType.OK:
            return

        try:
            erase_all_data()
        except OSError as e:
            show_message_dialog(self, "Couldn't Erase Data", str(e))
            return

        restart_process()  # never returns on success

    def _on_uninstall(self, _btn):
        confirm = Gtk.MessageDialog(
            transient_for=self, flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Uninstall Cinnamon Presets?",
        )
        confirm.format_secondary_text(
            "Removes the installed app, its menu entry, icon, and helper "
            "scripts. Your saved presets are kept unless you check the "
            "box below."
        )
        purge_check = Gtk.CheckButton(label="Also delete my saved presets and settings")
        confirm.get_content_area().pack_start(purge_check, False, False, 6)
        confirm.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        uninstall_btn = confirm.add_button("Uninstall", Gtk.ResponseType.OK)
        uninstall_btn.get_style_context().add_class("destructive-action")
        confirm.show_all()
        response = confirm.run()
        purge = purge_check.get_active()
        confirm.destroy()
        if response != Gtk.ResponseType.OK:
            return

        if purge:
            second = Gtk.MessageDialog(
                transient_for=self, flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.NONE,
                text="This cannot be undone.",
            )
            second.format_secondary_text(
                f"Your saved presets and settings at {CONFIG_DIR} will be "
                "permanently deleted along with the app."
            )
            # Same idea as Erase All Data's dialog: the export option stays
            # plain, only the actual destructive action gets the red
            # destructive-action styling.
            second.add_button("Export Presets First", Gtk.ResponseType.HELP)
            second.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
            delete_btn = second.add_button("Delete Everything", Gtk.ResponseType.OK)
            delete_btn.get_style_context().add_class("destructive-action")
            second.show_all()
            second_response = second.run()
            second.destroy()
            if second_response == Gtk.ResponseType.HELP:
                if self.main_window is not None:
                    self.main_window.on_export(None)
                return
            if second_response != Gtk.ResponseType.OK:
                return

        result = uninstall_app(purge=purge)
        if result["errors"]:
            show_message_dialog(
                self, "Uninstall Finished With Errors",
                "Some files couldn't be removed:\n" + "\n".join(result["errors"]),
            )
            return

        goodbye = Gtk.MessageDialog(
            transient_for=self, flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Uninstalled — goodbye!",
        )
        goodbye.run()
        goodbye.destroy()
        Gtk.main_quit()
        sys.exit(0)

    # --- Backups (b-lite) ----------------------------------------------

    BACKUP_ROWS = [
        ("lightdm", "Lock Screen (LightDM)", lightdm_backup_exists, restore_lightdm_backup),
        ("plymouth", "Boot Animation (Plymouth)", plymouth_backup_exists, restore_plymouth_backup),
        ("grub", "GRUB Bootloader", grub_backup_exists, restore_grub_backup),
    ]

    def _build_backups_page(self):
        scroll, box = self._scrolled_page()
        note = Gtk.Label(
            xalign=0,
            label="Exactly one rolling backup per item — the same one "
                  "Apply already creates before every overwrite. This just "
                  "centralizes what's otherwise only reachable from "
                  "whichever preset's Apply dialog happened to make it.",
        )
        note.set_line_wrap(True)
        box.pack_start(note, False, False, 0)

        self._backup_rows = {}
        for key, label, exists_fn, restore_fn in self.BACKUP_ROWS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
            status_label = Gtk.Label(xalign=1)
            row.pack_start(status_label, False, False, 0)
            restore_btn = Gtk.Button(label="Restore")
            restore_btn.connect("clicked", self._on_restore_backup, key, label, restore_fn)
            row.pack_start(restore_btn, False, False, 0)
            box.pack_start(row, False, False, 0)
            self._backup_rows[key] = (status_label, restore_btn, exists_fn)

        self._refresh_backup_rows()
        return scroll

    def _refresh_backup_rows(self):
        for key, (status_label, restore_btn, exists_fn) in self._backup_rows.items():
            exists = exists_fn()
            status_label.set_text("Backup available" if exists else "No backup")
            restore_btn.set_sensitive(exists)

    def _on_restore_backup(self, _btn, key, label, restore_fn):
        confirm = Gtk.MessageDialog(
            transient_for=self, flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Restore the previous {label} configuration?",
        )
        confirm.format_secondary_text(
            "Needs admin rights and will ask you to authenticate."
        )
        response = confirm.run()
        confirm.destroy()
        if response != Gtk.ResponseType.YES:
            return

        def work():
            return restore_fn()

        def on_done(result, error):
            if error is not None:
                show_message_dialog(self, "Restore Failed", str(error))
            else:
                show_message_dialog(self, "Restore Done", result or "Restored.")
            self._refresh_backup_rows()

        run_with_progress(self, f"Restoring {label}", "Waiting on admin authentication if needed…", work, on_done)

    # --- Updates -------------------------------------------------------

    def _build_updates_page(self):
        scroll, box = self._scrolled_page()

        box.pack_start(Gtk.Label(label=f"Current version: {VERSION}", xalign=0), False, False, 0)

        check_btn = Gtk.Button(label="Check Now")
        check_btn.set_halign(Gtk.Align.START)
        check_btn.connect("clicked", self._on_check_updates_now)
        box.pack_start(check_btn, False, False, 0)

        self.updates_status_label = Gtk.Label(label="", xalign=0)
        self.updates_status_label.set_line_wrap(True)
        box.pack_start(self.updates_status_label, False, False, 0)

        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)
        throttle_note = Gtk.Label(
            xalign=0,
            label=f"The app also checks silently in the background, at most "
                  f"once every {UPDATE_CHECK_INTERVAL_SECONDS // 3600} hours. "
                  "\"Check Now\" always bypasses that and checks immediately.",
        )
        throttle_note.set_line_wrap(True)
        throttle_note.get_style_context().add_class("dim-label")
        box.pack_start(throttle_note, False, False, 0)

        return scroll

    def _on_check_updates_now(self, _btn):
        self.updates_status_label.set_text("Checking…")

        def worker():
            result = check_for_updates()
            GLib.idle_add(self._on_updates_page_check_done, result)

        threading.Thread(target=worker, daemon=True).start()

    def _on_updates_page_check_done(self, result):
        _save_last_update_check_time()
        status = result.get("status")
        if status == "update_available":
            self.updates_status_label.set_text(f"Update available: {result.get('latest')} (you have {VERSION}).")
            if self.main_window is not None:
                self.main_window._show_update_banner(result.get("latest"), result.get("url"))
        elif status == "up_to_date":
            self.updates_status_label.set_text(f"You're up to date ({VERSION}).")
        elif status == "not_configured":
            self.updates_status_label.set_text("This build doesn't have a repo URL set yet.")
        else:
            self.updates_status_label.set_text(f"Couldn't check: {result.get('message', 'unknown error')}")
        return False

    # --- About -----------------------------------------------------------

    def _build_about_page(self):
        scroll, box = self._scrolled_page()

        name_label = Gtk.Label(xalign=0)
        name_label.set_markup(f"<span size='x-large'><b>{GLib.markup_escape_text(APP_NAME)}</b></span>")
        box.pack_start(name_label, False, False, 0)

        version_label = Gtk.Label(label=f"Version {VERSION}", xalign=0)
        version_label.get_style_context().add_class("dim-label")
        box.pack_start(version_label, False, False, 0)

        desc_label = Gtk.Label(
            xalign=0,
            label="A preset manager for your Cinnamon desktop look — theme, "
                  "icons, cursor, wallpaper, panel layout and applet "
                  "settings, extensions, sound, and optionally the login "
                  "screen, boot splash, and bootloader — all switchable "
                  "in one click.\n\nGRUB support is untested — use with "
                  "caution.",
        )
        desc_label.set_line_wrap(True)
        box.pack_start(desc_label, False, False, 0)

        links_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.pack_start(links_box, False, False, 0)
        repo_btn = build_icon_text_button("github", "Repository")
        repo_btn.connect("clicked", self._on_about_link, GITHUB_REPO_URL, "GitHub")
        links_box.pack_start(repo_btn, False, False, 0)

        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        license_label = Gtk.Label(xalign=0)
        license_label.set_line_wrap(True)
        license_label.set_markup(
            "<b>Licensed under the GPLv3.</b> In short: this software is "
            "free to use, study, share, and modify — including "
            "commercially — but anything built on it and distributed to "
            "others must also be released under the GPLv3, with source "
            "available. (This is a plain-English summary, not the "
            "license itself.)"
        )
        box.pack_start(license_label, False, False, 0)

        license_link_btn = Gtk.LinkButton.new_with_label("", "Read the full LICENSE")
        license_link_btn.set_halign(Gtk.Align.START)
        license_link_btn.connect("clicked", self._on_license_link)
        box.pack_start(license_link_btn, False, False, 0)

        legal_label = Gtk.Label(
            xalign=0,
            label="This application is not associated with the Cinnamon team.",
        )
        legal_label.get_style_context().add_class("dim-label")
        box.pack_start(legal_label, False, False, 0)

        return scroll

    def _on_about_link(self, _btn, url, label):
        if self.main_window is not None:
            self.main_window._on_footer_link(_btn, url, label)

    def _on_license_link(self, _btn):
        if GITHUB_REPO_URL:
            webbrowser.open(GITHUB_REPO_URL.rstrip("/") + "/blob/main/LICENSE")
        else:
            show_message_dialog(
                self, "Repository Not Configured",
                "This build doesn't have a repo URL set yet, so there's "
                "nowhere to link the license to.",
            )


class CinnamonPresetsWindow(Gtk.Window):
    GRID_MIN_THUMB = 90
    GRID_MAX_THUMB = 260
    GRID_DEFAULT_THUMB = 160
    # BETA-0.10: was one square LIST_THUMB_SIZE (56x56) — screenshots are
    # 16:9, so a square crop was cutting them oddly. Also bumped up
    # noticeably (old square was 56x56 = 3,136px²; this is 120x67 =
    # 8,040px², well over double the area) per feedback that list-view
    # thumbnails read too small.
    LIST_THUMB_WIDTH = 120
    LIST_THUMB_HEIGHT = 68  # round(120 * 9/16)

    def __init__(self):
        super().__init__(title=f"{APP_NAME} ({VERSION})")
        self.set_default_size(760, 640)
        self.set_border_width(12)

        app_settings = load_app_settings()
        self.view_mode = app_settings["default_view_mode"]
        self.thumb_size = app_settings["default_thumb_size"]
        self.sort_mode = app_settings["default_sort_mode"]
        self._pending_update_url = None

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(vbox)

        # --- update banner: slim, non-blocking, hidden until there's --------
        # actually something to say. Roadmap Phase 8 explicitly calls for
        # an InfoBar over a modal dialog here — set_no_show_all(True) so
        # the window's own show_all() (in main()) can't accidentally
        # reveal it; only _show_update_banner() ever makes it visible.
        self.update_infobar = Gtk.InfoBar()
        self.update_infobar.set_message_type(Gtk.MessageType.INFO)
        self.update_infobar.set_show_close_button(True)
        self.update_infobar.add_button("Update Now", Gtk.ResponseType.OK)
        self.update_infobar.connect("response", self._on_update_infobar_response)
        self.update_infobar.set_no_show_all(True)
        self.update_infobar.set_visible(False)
        self.update_infobar_label = Gtk.Label(xalign=0)
        self.update_infobar.get_content_area().pack_start(self.update_infobar_label, True, True, 0)
        vbox.pack_start(self.update_infobar, False, False, 0)

        # --- top row: search + the Import/Export "I/O duo" -----------------
        # Import/Export are neither pure browsing controls (Sort/Grid/List,
        # row below) nor selection-gated preset actions (Apply/Rename/
        # Delete/Save, bottom row) -- they're their own category: ways to
        # move a preset in or out of the app. Kept together, visually
        # linked into one segmented unit (GTK's "linked" style class), on
        # the most prominent row in the window rather than folded into
        # either neighboring group.
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_start(top_row, False, False, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search presets…")
        self.search_entry.connect("search-changed", lambda _e: self.refresh_list())
        top_row.pack_start(self.search_entry, True, True, 0)

        io_pair = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        io_pair.get_style_context().add_class("linked")
        top_row.pack_start(io_pair, False, False, 0)

        import_btn = build_icon_text_button("import", "Import")
        import_btn.connect("clicked", self.on_import)
        io_pair.pack_start(import_btn, False, False, 0)

        self.export_btn = build_icon_text_button("export", "Export")
        self.export_btn.connect("clicked", self.on_export)
        io_pair.pack_start(self.export_btn, False, False, 0)

        # Thumbnail size/Sort/Grid/List + the actual list live together
        # inside one bordered panel, per the reference mockup -- visually
        # distinct from the Search/Import/Export row above, which stays
        # outside/unboxed.
        browse_frame = Gtk.Frame()
        browse_frame.set_shadow_type(Gtk.ShadowType.IN)
        vbox.pack_start(browse_frame, True, True, 0)

        browse_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        browse_box.set_border_width(8)
        browse_frame.add(browse_box)

        # --- browsing controls: thumbnail size slider (grid mode only —
        # file-manager style) sits on the left, Sort/Grid/List anchored
        # right, one row either way -----------------------------------
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        browse_box.pack_start(toolbar, False, False, 0)

        self.size_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.pack_start(self.size_box, True, True, 0)
        self.size_box.pack_start(Gtk.Label(label="Thumbnail size:"), False, False, 0)
        self.size_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, self.GRID_MIN_THUMB, self.GRID_MAX_THUMB, 10,
        )
        self.size_scale.set_value(self.thumb_size)
        self.size_scale.set_draw_value(False)
        self.size_scale.set_hexpand(True)
        self.size_scale.connect("value-changed", self._on_thumb_size_changed)
        self.size_box.pack_start(self.size_scale, True, True, 0)
        self.size_box.set_visible(self.view_mode != "list")
        self.size_box.set_no_show_all(self.view_mode == "list")

        self.list_toggle = Gtk.ToggleButton(label="List")
        self.list_toggle.set_active(self.view_mode == "list")
        self.list_toggle.connect("toggled", self._on_view_toggle, "list")
        toolbar.pack_end(self.list_toggle, False, False, 0)

        self.grid_toggle = Gtk.ToggleButton(label="Grid")
        self.grid_toggle.set_active(self.view_mode != "list")
        self.grid_toggle.connect("toggled", self._on_view_toggle, "grid")
        toolbar.pack_end(self.grid_toggle, False, False, 0)

        self.sort_combo = Gtk.ComboBoxText()
        self.sort_combo.append("name", "Sort by: Name")
        self.sort_combo.append("date", "Sort by: Date Saved")
        self.sort_combo.set_active_id(self.sort_mode)
        self.sort_combo.connect("changed", self._on_sort_changed)
        toolbar.pack_end(self.sort_combo, False, False, 0)

        # --- the list itself, or an empty-state message ---
        # BETA-0.16: this used to be a Gtk.Stack switching between the two
        # views by name. In testing, the Stack's visible child kept
        # getting allocated 1x1 regardless of transition-type, timing, or
        # forced resizes/queue_resize() -- content existed, was correctly
        # marked as the visible child, and still never received real
        # layout space. Plain show()/hide() on a simple Box sidesteps
        # whatever that Stack-specific allocation quirk was, with
        # identical visible behavior (exactly one of the two shown).
        self.list_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.list_container.set_vexpand(True)
        browse_box.pack_start(self.list_container, True, True, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_row_spacing(4)
        self.flowbox.set_column_spacing(4)
        self.flowbox.connect("selected-children-changed", lambda _fb: self._update_action_sensitivity())
        # Gtk.SelectionMode.SINGLE has no built-in way to get back to
        # "nothing selected" by clicking -- clicking the already-selected
        # item just re-confirms it by default, and there's no handling at
        # all for clicking empty space. See _on_flowbox_background_click
        # for the two deselection paths (BETA-0.16 shipped path 1 only,
        # which turned out unreliable; BETA-0.17 adds path 2, which is
        # the one that's actually consistent).
        self.flowbox.connect("button-press-event", self._on_flowbox_background_click)
        scroll.add(self.flowbox)
        self.list_container.pack_start(scroll, True, True, 0)
        self._presets_view = scroll

        # Empty state matches the mockup: a big "+" glyph over a short
        # prompt, rather than a plain sentence -- reads as an inviting
        # action target instead of just an absence-of-content notice.
        empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        empty_box.set_hexpand(True)
        empty_box.set_vexpand(True)
        empty_box.set_valign(Gtk.Align.CENTER)
        empty_box.set_halign(Gtk.Align.CENTER)

        plus_label = Gtk.Label(xalign=0.5)
        plus_label.set_markup('<span size="48000" weight="bold">+</span>')
        plus_label.get_style_context().add_class("dim-label")
        empty_box.pack_start(plus_label, False, False, 0)

        self.empty_label = Gtk.Label(label="Create or Import a new preset")
        self.empty_label.set_line_wrap(True)
        self.empty_label.set_max_width_chars(50)
        self.empty_label.set_justify(Gtk.Justification.CENTER)
        self.empty_label.get_style_context().add_class("dim-label")
        empty_box.pack_start(self.empty_label, False, False, 0)

        self.list_container.pack_start(empty_box, True, True, 0)
        self._empty_view = empty_box

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_start(btn_box, False, False, 0)

        self.apply_btn = Gtk.Button(label="Apply")
        self.apply_btn.connect("clicked", self.on_apply)
        btn_box.pack_start(self.apply_btn, True, True, 0)

        self.rename_btn = Gtk.Button(label="Rename")
        self.rename_btn.connect("clicked", self.on_rename)
        btn_box.pack_start(self.rename_btn, True, True, 0)

        self.delete_btn = Gtk.Button(label="Delete")
        self.delete_btn.connect("clicked", self.on_delete)
        btn_box.pack_start(self.delete_btn, True, True, 0)

        # Phase 5: System Boot Settings used to be a separate button/dialog
        # from Apply — now ApplyPresetDialog covers Theme + Lock Screen +
        # Boot Animation + GRUB in one page, so there's just the one entry
        # point below.

        self.save_btn = Gtk.Button(label="+ Save Current Desktop As New Preset")
        self.save_btn.connect("clicked", self.on_save_new)
        vbox.pack_start(self.save_btn, False, False, 0)

        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_start(footer_box, False, False, 0)

        update_btn = Gtk.Button(label="Check for Updates")
        update_btn.connect("clicked", self.on_check_updates)
        footer_box.pack_start(update_btn, True, True, 0)

        # Roadmap Phase 9: real Settings page now exists — About's old
        # content moved into SettingsWindow's own About section (see
        # on_settings() below).
        settings_btn = build_icon_text_button("settings", "Settings")
        settings_btn.connect("clicked", self.on_settings)
        footer_box.pack_start(settings_btn, True, True, 0)

        self.status_label = Gtk.Label(label="", xalign=0)
        self.status_label.set_line_wrap(True)
        self.status_label.set_max_width_chars(70)
        vbox.pack_start(self.status_label, False, False, 0)

        # --- footer: support links + app identity/legal --------------------
        # BETA-0.10: was entirely missing from the app. Links are best-
        # effort — PATREON_URL/YOUTUBE_URL/GITHUB_REPO_URL are still empty
        # placeholders (see the TODO near their definitions), so clicking
        # one before they're filled in just reports that instead of
        # opening a broken/empty URL.
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        vbox.pack_start(footer, False, False, 0)

        support_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        footer.pack_start(support_box, False, False, 0)

        support_label = Gtk.Label(label="Support the project:", xalign=0)
        support_label.get_style_context().add_class("dim-label")
        support_box.pack_start(support_label, False, False, 0)

        links_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        support_box.pack_start(links_box, False, False, 0)
        for icon_name, label, url in (
            ("patreon", "Patreon", PATREON_URL),
            ("youtube", "YouTube", YOUTUBE_URL),
            ("github", "GitHub", GITHUB_REPO_URL),
        ):
            # Real brand icon if icons/ui/<name>.svg exists (source from
            # each platform's official brand kit — these three exist for
            # trademark recognition, not for us to reinterpret the way
            # this app's own category icons are); gracefully degrades to
            # a plain text button via build_icon_text_button's existing
            # fallback if the file isn't there yet.
            link_btn = build_icon_text_button(icon_name, label, size=16)
            link_btn.set_relief(Gtk.ReliefStyle.NONE)
            link_btn.connect("clicked", self._on_footer_link, url, label)
            links_box.pack_start(link_btn, False, False, 0)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)
        info_box.set_valign(Gtk.Align.CENTER)
        footer.pack_start(info_box, True, True, 0)

        identity_label = Gtk.Label(
            label=f"<b>{GLib.markup_escape_text(APP_NAME)}</b>\nVersion {GLib.markup_escape_text(VERSION)}",
            use_markup=True, xalign=1, justify=Gtk.Justification.RIGHT,
        )
        info_box.pack_start(identity_label, False, False, 0)

        legal_label = Gtk.Label(
            label=(
                "This application is not associated with the Cinnamon team.\n"
                "© Licensed under GPLv3"
            ),
            xalign=1, justify=Gtk.Justification.RIGHT,
        )
        legal_label.set_line_wrap(True)
        legal_label.set_max_width_chars(45)
        legal_label.get_style_context().add_class("dim-label")
        info_box.pack_start(legal_label, False, False, 0)

        self._update_action_sensitivity()
        # BETA-0.16 fix: calling refresh_list() synchronously here used to
        # leave the list_stack showing "presets" even with zero presets
        # saved -- Gtk.Stack.set_visible_child_name() doesn't reliably
        # stick when called before the top-level window has ever been
        # realized/shown, same underlying class of bug as the earlier
        # ApplyPresetDialog blank-dialog fix (toggling descendant state
        # before the ancestor window is part of a show pass). Deferred to
        # an idle callback so it runs after main() calls show_all().
        GLib.idle_add(lambda: self.refresh_list() or False)

        # Roadmap Phase 8: throttled silent startup check, small delay so
        # it doesn't compete with the window's own first paint. Only ever
        # surfaces anything if an update is actually found (the banner) —
        # silent otherwise, unlike the manual "Check Now" button.
        GLib.timeout_add_seconds(2, self._maybe_auto_check_updates)

    def _on_footer_link(self, _btn, url, label):
        if not url:
            self.set_status(f"{label} link isn't set yet.")
            return
        webbrowser.open(url)

    # --- list building -----------------------------------------------------

    def refresh_list(self):
        """Rebuilds the FlowBox from scratch: reads every preset's meta,
        applies the search filter and sort order, then renders grid or
        list cards depending on the current view mode. Preserves the
        current selection across a rebuild where possible (e.g. after a
        thumbnail-size change), so the action buttons don't flicker
        disabled/enabled for no reason."""
        previously_selected = self.get_selected_name()

        for child in list(self.flowbox.get_children()):
            self.flowbox.remove(child)

        query = self.search_entry.get_text().strip().lower()
        entries = []
        for name in list_presets():
            meta = load_meta(name)
            haystack = f"{meta.get('name', name)} {meta.get('description', '')}".lower()
            if query and query not in haystack:
                continue
            entries.append((name, meta))

        if self.sort_mode == "date":
            entries.sort(key=lambda e: e[1].get("saved_at") or "", reverse=True)
        else:
            entries.sort(key=lambda e: (e[1].get("name") or e[0]).lower())

        if self.view_mode == "grid":
            self.flowbox.set_min_children_per_line(1)
            self.flowbox.set_max_children_per_line(12)
        else:
            self.flowbox.set_min_children_per_line(1)
            self.flowbox.set_max_children_per_line(1)

        build_child = self._build_grid_child if self.view_mode == "grid" else self._build_list_child
        for name, meta in entries:
            content = build_child(name, meta)
            fb_child = Gtk.FlowBoxChild()
            fb_child.preset_name = name
            fb_child.add(content)
            self.flowbox.add(fb_child)

        self.flowbox.show_all()
        if entries:
            self._presets_view.show()
            self._empty_view.hide()
        else:
            self._presets_view.hide()
            self._empty_view.show()

        if previously_selected:
            for child in self.flowbox.get_children():
                if getattr(child, "preset_name", None) == previously_selected:
                    self.flowbox.select_child(child)
                    break

        self._update_action_sensitivity()

    def _build_grid_child(self, name, meta):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_size_request(self.thumb_size + 16, -1)

        thumb_w = self.thumb_size
        thumb_h = max(1, round(thumb_w * 9 / 16))
        pixbuf = load_thumbnail_pixbuf(PRESETS_DIR / name, meta, thumb_w, thumb_h)
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.IN)
        frame.set_halign(Gtk.Align.CENTER)
        frame.add(image)
        box.pack_start(frame, False, False, 0)

        label = Gtk.Label(label=meta.get("name", name), xalign=0.5)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(max(8, thumb_w // 10))
        label.set_justify(Gtk.Justification.CENTER)
        box.pack_start(label, False, False, 0)

        if meta.get("description"):
            box.set_tooltip_text(meta["description"])
        return box

    def _build_list_child(self, name, meta):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(6)
        box.set_margin_end(6)

        w, h = self.LIST_THUMB_WIDTH, self.LIST_THUMB_HEIGHT
        pixbuf = load_thumbnail_pixbuf(PRESETS_DIR / name, meta, w, h)
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.IN)
        frame.add(image)
        box.pack_start(frame, False, False, 0)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_valign(Gtk.Align.CENTER)
        name_label = Gtk.Label(label=meta.get("name", name), xalign=0)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        text_box.pack_start(name_label, False, False, 0)
        if meta.get("description"):
            desc_label = Gtk.Label(label=meta["description"], xalign=0)
            desc_label.set_ellipsize(Pango.EllipsizeMode.END)
            desc_label.get_style_context().add_class("dim-label")
            text_box.pack_start(desc_label, False, False, 0)
        box.pack_start(text_box, True, True, 0)
        return box

    def _on_view_toggle(self, btn, mode):
        if not btn.get_active():
            return  # this fires for the button being turned OFF too; ignore that half
        self.view_mode = mode
        other = self.list_toggle if mode == "grid" else self.grid_toggle
        if other.get_active():
            other.set_active(False)
        self.size_box.set_visible(mode == "grid")
        self.size_box.set_no_show_all(mode != "grid")
        self.refresh_list()

    def _on_thumb_size_changed(self, scale):
        self.thumb_size = int(scale.get_value())
        if self.view_mode == "grid":
            self.refresh_list()

    def _on_sort_changed(self, combo):
        self.sort_mode = combo.get_active_id() or "name"
        self.refresh_list()

    def get_selected_name(self):
        children = self.flowbox.get_selected_children()
        return children[0].preset_name if children else None

    def _select_by_name(self, name):
        """Explicitly select a preset after an action that would otherwise
        lose the selection on refresh_list()'s rebuild — e.g. after a
        rename (the old folder name no longer exists to match against) or
        right after creating a new preset."""
        for child in self.flowbox.get_children():
            if getattr(child, "preset_name", None) == name:
                self.flowbox.select_child(child)
                break
        self._update_action_sensitivity()

    def _on_flowbox_background_click(self, flowbox, event):
        """Two deselection paths, because relying on just one turned out
        to be inconsistent (BETA-0.16 -> reported still flaky in
        BETA-0.17):

        1. Click lands on true empty space (nothing at that position at
           all) -> clear the selection. get_child_at_pos returns None
           for that case.
        2. Click lands on the tile that's ALREADY selected -> toggle it
           off instead of letting GTK's default SINGLE-mode handling
           just re-confirm the same selection (which is what it
           normally does — clicking a selected item again is a no-op by
           default). This is the actually-reliable path: a
           FlowBoxChild's hit area is its whole grid cell, not just the
           visible thumbnail/label inside it — homogeneous sizing and
           per-cell stretch mean a lot of space that LOOKS empty around
           a tile is still technically "on" that child, not background,
           so path 1 alone only worked when a click happened to land in
           genuinely unclaimed space (below the last row, right of the
           last column). Toggling the exact already-selected child has
           no such ambiguity — it's not coordinate-dependent at all.
        """
        if event.button != 1:
            return False
        child = flowbox.get_child_at_pos(int(event.x), int(event.y))
        if child is None:
            flowbox.unselect_all()
            return False
        if child in flowbox.get_selected_children():
            flowbox.unselect_all()
            return True  # stop the default handler from re-selecting it right back
        return False

    def _update_action_sensitivity(self):
        """Selecting a preset is what unlocks everything else — Apply,
        Rename, and Delete all stay grayed out until something's actually
        selected, so the app never invites acting on nothing."""
        has_selection = self.get_selected_name() is not None
        self.apply_btn.set_sensitive(has_selection)
        self.rename_btn.set_sensitive(has_selection)
        self.delete_btn.set_sensitive(has_selection)
        self.export_btn.set_sensitive(has_selection)

        # Whichever of the two "what do I do next" actions is actually
        # usable right now gets the theme-adaptive highlight -- Save when
        # there's nothing to Apply yet, Apply once something's selected.
        # Never both, mirroring the sensitivity state exactly.
        apply_style = self.apply_btn.get_style_context()
        save_style = self.save_btn.get_style_context()
        if has_selection:
            apply_style.add_class("suggested-action")
            save_style.remove_class("suggested-action")
        else:
            save_style.add_class("suggested-action")
            apply_style.remove_class("suggested-action")
        self.apply_btn.queue_draw()
        self.save_btn.queue_draw()

    def set_status(self, text):
        self.status_label.set_text(text)
        GLib.timeout_add_seconds(6, lambda: self.status_label.set_text("") or False)

    def on_apply(self, _btn):
        name = self.get_selected_name()
        if not name:
            self.set_status("Select a preset first.")
            return
        dialog = ApplyPresetDialog(self, name)
        dialog.run()
        dialog.destroy()
        # Whatever happened (theme applied, a boot item applied, nothing
        # touched at all) was already reported inline inside the dialog
        # itself — no need to guess at a summary here.
        self.refresh_list()

    def on_delete(self, _btn):
        name = self.get_selected_name()
        if not name:
            self.set_status("Select a preset first.")
            return
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete preset '{name}'?",
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            delete_preset(name)
            self.refresh_list()
            self.set_status(f"Deleted '{name}'.")

    def on_rename(self, _btn):
        name = self.get_selected_name()
        if not name:
            self.set_status("Select a preset first.")
            return
        new_name = self._ask_name("Rename Preset", name)
        if new_name and new_name != name:
            try:
                rename_preset(name, new_name)
                self.refresh_list()
                self._select_by_name(new_name)
                self.set_status(f"Renamed to '{new_name}'.")
            except Exception as e:
                self.set_status(f"Error: {e}")

    def on_export(self, _btn):
        name = self.get_selected_name()
        if not name:
            self.set_status("Select a preset first.")
            return
        meta = load_meta(name)
        if (meta.get("screenshot") or {}).get("status") != "saved":
            show_message_dialog(
                self, "No Screenshot Yet",
                f"'{name}' doesn't have a screenshot, so there's nothing to "
                "show whoever you share it with. Give it one (re-save it "
                "with a screenshot) before exporting.",
                Gtk.MessageType.WARNING,
            )
            return
        dialog = ExportDialog(self, name, meta)
        dialog.run()
        # ExportDialog's own response handler decides for itself whether
        # to stay open (cancel/error) or destroy() (success) -- run()
        # returning here just means the whole dialog is gone one way or
        # the other, nothing left for this handler to do but refresh.
        self.refresh_list()

    def on_import(self, _btn):
        chooser = Gtk.FileChooserDialog(
            title="Import Preset", transient_for=self, action=Gtk.FileChooserAction.OPEN,
        )
        chooser.set_default_size(720, 520)
        chooser.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.OK)
        filt = Gtk.FileFilter()
        filt.set_name("Cinnamon Presets archive (*.tar.gz)")
        filt.add_pattern("*.tar.gz")
        chooser.add_filter(filt)
        response = chooser.run()
        archive_path = chooser.get_filename() if response == Gtk.ResponseType.OK else None
        chooser.destroy()
        if not archive_path:
            return

        try:
            top_level = _peek_archive_name(archive_path)
            candidate_name = sanitize_name(top_level)
            archive_meta = _peek_archive_meta(archive_path, top_level)
        except ImportInvalidArchive as e:
            show_message_dialog(self, "Import Failed", str(e), Gtk.MessageType.ERROR)
            return

        final_name = candidate_name
        if (PRESETS_DIR / final_name).exists():
            final_name = self._ask_name(
                f"'{candidate_name}' Already Exists — Choose a Different Name", candidate_name,
            )
            if not final_name:
                return  # cancelled the rename prompt -- nothing imported, nothing touched

        preview = ImportPreviewDialog(self, final_name, archive_meta)
        preview_response = preview.run()
        preview.destroy()
        if preview_response != Gtk.ResponseType.OK:
            return

        def work(cancel_event, progress_cb):
            return import_preset(archive_path, final_name, cancel_event, progress_cb)

        def on_done(result, error, cancelled):
            if cancelled:
                show_message_dialog(self, "Import Cancelled", "No preset was imported.")
            elif error is not None:
                show_message_dialog(self, "Import Failed", str(error), Gtk.MessageType.ERROR)
            else:
                self.refresh_list()
                self._select_by_name(final_name)
                self.set_status(f"Imported '{final_name}'.")

        run_export_with_progress(
            self, "Importing Preset", f"Importing '{final_name}'…", work, on_done,
        )

    def on_save_new(self, _btn):
        wizard = SavePresetWizard(self)
        wizard.connect("response", self._on_save_wizard_response)

    def _on_save_wizard_response(self, dialog, response):
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        name = dialog.get_name()
        description = dialog.get_description()
        selected_categories = dialog.get_selected_categories()
        pixbuf = dialog.result_pixbuf

        # Save is only ever clickable once both mandatory fields are
        # filled (see SavePresetWizard._update_save_sensitivity), but
        # double-check rather than trust button state alone.
        if not name or pixbuf is None:
            return

        existing_dir = PRESETS_DIR / sanitize_name(name)
        if existing_dir.exists():
            confirm = Gtk.MessageDialog(
                transient_for=dialog,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"A preset named '{name}' already exists.",
            )
            confirm.format_secondary_text("Overwrite it?")
            overwrite_response = confirm.run()
            confirm.destroy()
            if overwrite_response != Gtk.ResponseType.YES:
                # Leave the wizard open, screenshot/description intact,
                # so they can just retype the name instead of starting
                # the whole save over.
                return

        dialog.destroy()

        def work():
            preset_dir, meta = save_preset(name, description, selected_categories)
            save_screenshot(preset_dir, pixbuf)
            update_preset_meta(name, "screenshot", {"status": "saved", "file": SCREENSHOT_FILENAME})
            return preset_dir, meta

        def on_done(result, error):
            if error is not None:
                self.set_status(f"Error: {error}")
                return
            preset_dir, meta = result

            self.refresh_list()
            self._select_by_name(name)

            plymouth_meta = meta.get("plymouth") or {}
            if plymouth_meta.get("status") == "not_found" and selected_categories.get("plymouth", True):
                self._offer_plymouth_root_retry(name, preset_dir)

            self.set_status(f"Saved '{name}'.")

        run_with_progress(self, "Saving Preset", f"Saving '{name}'…", work, on_done)

    def _offer_plymouth_root_retry(self, name, preset_dir):
        """Plymouth theme detection without root came up empty (see
        save_plymouth/_plymouth_current_theme). On some systems even
        *reading* the current theme needs admin rights. Ask before doing
        anything about it — this is its own separate pkexec prompt, only
        ever used for this one read-only check, and grants nothing beyond
        it: no credentials are kept, so saving again later asks again."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Couldn't detect your Plymouth boot-splash theme.",
        )
        dialog.format_secondary_text(
            "Reading it needs admin rights on this system. Grant one-time "
            "access just to check the current theme name?\n\n"
            "Nothing else is touched, and the access isn't kept — you'll "
            "be asked again next time you save a preset."
        )
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.YES:
            return
        try:
            entry = save_plymouth_with_root(preset_dir)
            update_preset_meta(name, "plymouth", entry)
            self.set_status(f"Plymouth theme '{entry.get('theme')}' saved.")
        except Exception as e:
            self._info_dialog(
                "Couldn't Read Plymouth Theme",
                f"{e}\n\nThe rest of '{name}' was still saved fine — just "
                "without a Plymouth theme.",
            )

    def _maybe_auto_check_updates(self):
        if _should_auto_check_updates():
            self._run_update_check(silent=True)
        return False  # GLib.timeout_add one-shot

    def on_check_updates(self, _btn):
        self.set_status("Checking for updates…")
        self._run_update_check(silent=False)

    def _run_update_check(self, silent):
        """Runs check_for_updates() on a background thread either way —
        it's a network call with its own timeout, no reason to block the
        main loop for the manual button either now that run_with_progress
        already established the pattern elsewhere in this app."""
        def worker():
            result = check_for_updates()
            GLib.idle_add(self._on_update_check_done, result, silent)

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_check_done(self, result, silent):
        _save_last_update_check_time()
        status = result.get("status")

        if status == "update_available":
            self._show_update_banner(result.get("latest"), result.get("url"))
            if not silent:
                self.set_status("")
            return False

        # Everything below is only worth interrupting the person for on a
        # manual check they explicitly asked for -- a silent background
        # check finding nothing new (or failing) shouldn't say anything.
        if silent:
            return False

        if status == "not_configured":
            self._info_dialog(
                "Update Checker Not Configured",
                "This build doesn't have a repo URL set yet, so it can't "
                "check GitHub for a newer release.",
            )
        elif status == "error":
            self._info_dialog("Couldn't Check for Updates", result.get("message", "Unknown error."))
        elif status == "up_to_date":
            self.set_status(f"You're up to date ({VERSION}).")
        return False

    def _show_update_banner(self, latest, url):
        self._pending_update_url = url
        self.update_infobar_label.set_text(f"Update available: {latest} (you have {VERSION}).")
        self.update_infobar.set_visible(True)

    def _on_update_infobar_response(self, infobar, response_id):
        if response_id == Gtk.ResponseType.CLOSE:
            infobar.set_visible(False)
        elif response_id == Gtk.ResponseType.OK:
            self._perform_update_now()

    def _perform_update_now(self):
        self.update_infobar.set_visible(False)

        def work():
            return perform_git_update()

        def on_done(result, error):
            if error is not None:
                self._info_dialog("Update Failed", str(error))
                return

            ok, message = result
            if ok:
                self.set_status("Update applied — restarting…")
                # Brief pause so the status message actually renders
                # before the process image gets replaced out from under
                # it — os.execv() never returns on success.
                GLib.timeout_add(800, self._delayed_restart)
                return

            if _is_appimage():
                self._info_dialog(
                    "Manual Update Needed",
                    "Running as an AppImage — in-place self-update for "
                    "that isn't wired up yet (see the roadmap's Phase 8 "
                    "AppImage item). Download the new version from the "
                    "release page instead.",
                )
            else:
                self._info_dialog("Manual Update Needed", message)
            if self._pending_update_url:
                webbrowser.open(self._pending_update_url)

        run_with_progress(self, "Updating", "Downloading the latest version…", work, on_done)

    def _delayed_restart(self):
        restart_process()
        return False  # unreachable on success -- os.execv() replaces this process

    def on_settings(self, _btn):
        dialog = SettingsWindow(self)
        dialog.stack.set_visible_child_name("about")
        dialog.run()
        dialog.destroy()
        # Storage/General settings may have changed the on-disk state
        # (Erase All Data restarts the process itself and never reaches
        # here; a plain Close does) — refresh so the list reflects
        # anything that did change (e.g. a migration re-run).
        self.refresh_list()

    def _info_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def _ask_name(self, title, default_text):
        dialog = Gtk.Dialog(title=title, transient_for=self, flags=0)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
        )
        entry = Gtk.Entry()
        entry.set_text(default_text)
        entry.set_activates_default(True)
        box = dialog.get_content_area()
        box.set_border_width(10)
        box.add(entry)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        response = dialog.run()
        text = entry.get_text().strip()
        dialog.destroy()
        if response == Gtk.ResponseType.OK and text:
            return text
        return None


def main():
    ensure_dirs()
    setup_logging()
    logger.info(f"--- {APP_NAME} {VERSION} starting ---")
    migrate_all_presets()
    win = CinnamonPresetsWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
