# Changelog

All notable changes to Cinnamon Presets, from the pre-1.0 beta series.

## 0.20.0

  - Fixed the app icon not showing up after a .deb install: the icon
    was only shipped under hicolor/128x128/apps, not the
    hicolor/scalable/apps location some lookups expect for a vector
    icon; it's now shipped in both places for every install method
    (.deb, AppImage, install.sh). Also set the app's prgname explicitly
    on startup and added StartupWMClass to the .desktop file, so the
    window/taskbar icon reliably matches regardless of how the app was
    launched, instead of depending on argv[0] happening to line up.
  - Redesigned the update banner: it's now a rounded, on-brand card
    (matching the app's own icon colors) instead of GTK's plain default
    blue InfoBar, clearly states the new version, and adds a "Learn
    more" link to the release notes alongside the existing Update Now
    button.
  - New: after updating, the next launch shows a one-time "What's New"
    popup with the changelog entries since the version you were
    previously on. Only fires on a real upgrade (a fresh install just
    silently remembers its own version, no popup) and only shows once
    per version.

## 0.19.0

  - Switched from BETA-x.y version strings to this project's own X.Y.Z
    scheme (X: 0 = beta, 1 = release; Y: minor; Z: bugfix).
  - Added .deb and AppImage packaging (see debian/ and
    packaging/appimage/), plus a GitHub Actions workflow that builds
    and publishes both on every version tag.
  - The in-app "Check for Updates" flow now recognizes how it's
    installed and updates itself the matching way: `git pull` for a
    source checkout, a pkexec-authorized `dpkg -i` for .deb, or an
    in-place file swap for AppImage (which then asks for a manual
    restart rather than trying to relaunch across its own FUSE mount).
  - Removed the GRUB "untested" warning and its apply-time cooldown,
    now that it's been verified working end-to-end. LightDM, Plymouth,
    and GRUB now share one consistent confirmation dialog on apply,
    rather than GRUB having its own separate wording.
  - Settings now opens on the General tab by default, instead of
    always landing on About.
  - Every helper script now has full inline documentation of what it
    does and why, matching the same treatment the main script already
    had.

## BETA-0.18 (bug fixes) adds

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

## BETA-0.17 (Roadmap Phase 9 — Settings Tab, plus a couple of loose ends)

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

## BETA-0.16 (Roadmap Phase 8 — Update System) adds

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

## BETA-0.15 (Roadmap Phase 7 — GRUB Safety Upgrade) adds

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

## BETA-0.14 (Roadmap Phase 6, part 2 — Import) adds

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

## BETA-0.13 (Roadmap Phase 6, part 1 — Export) adds

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

## BETA-0.12 (Roadmap Addendum — Progress Indicators, retrofitted into

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

## BETA-0.11 (Roadmap Phase 5 — Apply Flow Rebuild) adds

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

## BETA-0.9 (Roadmap Phase 3 — Data Model + Main List Rebuild) adds

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

## BETA-0.8 fixes another real bundling gap, found the same way as BETA-0.6

(reading Cinnamon Settings' own source, not guessing): LightDM's
`background=` image is now bundled, not just the config file that
references it — same class of bug the desktop wallpaper handling already
solved, just not applied to LightDM until now. Presets saved before
BETA-0.8 need a re-save to pick this up; applying an old one falls back
to LightDM's default background since there's nothing bundled yet.

## BETA-0.7 (Roadmap Phase 2 — Screenshot Capture Module) adds

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

## BETA-0.6 fixes real, verified dconf key mistakes found in BETA-0.5's

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

## BETA-0.5 (Roadmap Phase 1 — foundation) adds

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

## BETA-0.4 adds

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

## BETA-0.3 added

  - Bundling the actual files for any user-installed (non-stock) GTK/icon/
    cursor/sound theme and any user-installed extension/applet/desklet, so
    a preset still works after a fresh install or on another machine.
  - Optional, opt-in snapshotting and restoring of LightDM (login screen),
    Plymouth (boot splash), and GRUB (bootloader). These three are saved
    automatically (read-only, no root needed) whenever you save a preset,
    but applying each one is a separate, deliberate action that asks for
    admin rights on its own — authorizing one never grants access to the
    other two.
