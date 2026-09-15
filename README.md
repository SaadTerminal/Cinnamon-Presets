# Cinnamon Presets

A desktop preset manager for Linux Mint Cinnamon — save and switch
between full desktop "looks" in one click, the way Windows XP handled
visual styles.

A preset captures your GTK theme, icon theme, cursor theme and size,
wallpaper, panel layout and applets, extensions, desklets, and sound
theme as one switchable snapshot. Any user-installed (non-stock) theme
or extension has its actual files bundled into the preset too, so it
still works after a fresh install or on another machine.

Optionally, a preset can also snapshot and restore your login screen
(LightDM), boot splash (Plymouth), and bootloader (GRUB) config. These
three are captured automatically (read-only, no admin rights needed)
whenever you save a preset, but applying any of them is a separate,
deliberate action that asks you to authenticate — authorizing one
never grants access to the other two, and each can be reverted back to
what it was before, independently, from the same dialog.

## Installing

```bash
git clone https://github.com/SaadTerminal/Cinnamon-Presets.git
cd Cinnamon-Presets
./install.sh
```

This only ever copies files into `~/.local/bin`,
`~/.local/share/applications`, `~/.local/share/icons`, and
`~/.local/share/cinnamon-presets/helpers` — it never touches
`~/.config/cinnamon-presets`, which is where your saved presets live,
so reinstalling or upgrading is always safe for your presets. Nothing
in `install.sh` needs root; the only admin prompts you'll ever see
come later, inside the app itself, when you explicitly apply LightDM,
Plymouth, or GRUB.

Once installed, launch it from your applications menu as "Cinnamon
Presets", or run `cinnamon-presets` from a terminal (make sure
`~/.local/bin` is on your `PATH`).

### Requirements

- `python3-gi`, `gir1.2-gtk-3.0`, `python3-cairo`
- `dconf-cli`
- `policykit-1` (for `pkexec` — present by default on Linux Mint Cinnamon)

`update-grub` and `plymouth` are part of Mint's default install and
don't need to be installed separately.

### Uninstalling

```bash
./uninstall.sh
```

Removes the app but leaves your saved presets at
`~/.config/cinnamon-presets` untouched. Pass `--purge` if you want
those deleted too.

## How it works

Cinnamon keeps almost all of its visual state under one dconf tree,
`/org/cinnamon/`, but that tree also holds unrelated things
(favorite apps, keybindings). A preset saves an explicit allowlist of
theme-related keys and directories, one snapshot per category, plus
copies of anything those keys merely reference by name (wallpaper
image, custom themes, custom extensions). Applying a preset
writes/resets only those specific keys — never the whole tree —
restores any bundled theme or extension files, then asks Cinnamon to
reload itself. Every step is independent, so a failure in one category
or one file never blocks the rest.

## Status

This project is in beta, heading toward a 1.0 release. See
[CHANGELOG.md](CHANGELOG.md) for the version history.

## License

GPLv3 — see [LICENSE](LICENSE).
