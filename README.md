# Bleach Kitty · Bankai terminal theme

A character-driven Bleach theme for Kitty, Fish, Fastfetch and btop. Includes **32 characters, 40 portraits and 80 art editions**, with matching shell, cursor, greeting and monitor accents.

[Browse all color and manga artwork](files/.config/fastfetch/previews/manga-roster.html) · [Full command guide](files/.config/fastfetch/portraits/ROTATION.md) · [Artwork provenance and prompts](docs/ARTWORK.md)

| Color | Manga |
| --- | --- |
| ![Urahara in color](files/.config/fastfetch/portraits/urahara.png) | ![Urahara in manga ink](files/.config/fastfetch/manga/urahara.png) |

## Features

- Color, manga, or randomly mixed art editions.
- Persistent shuffle decks shared across Kitty tabs; equal turns per portrait or per character.
- Favorites, character groups, and session-only portrait selection.
- Responsive full/compact greetings, plus a saved off mode.
- Character-colored prompts, Git/status hints, cursor, window titles and btop themes.
- Recent-art history with exact-edition previews and replay.
- Settings overlay on **Ctrl+Shift+F12**.
- Setup diagnostics and verified theme snapshots.

## Bankai desktop apps

The [desktop source collection](desktop/README.md) includes both the original [Python + PySide6](desktop/python/README.md) control center and the experimental [Rust + Qt](desktop/rust/README.md) edition, with eight matching wallpapers and KDE color schemes. Desktop installation is separate from the terminal theme installer below.

## Requirements

Linux with `kitty`, `fish`, `fastfetch`, `btop`, `fzf`, and `python3` on PATH. `git` is optional for the right prompt. A font covering the Japanese heading and prompt symbols is recommended. Preview rendering uses `/usr/share/fzf/fzf-preview.sh` when supplied by the distribution; without it the picker still works, with a text fallback.

Originally developed on CachyOS/KDE. The packaged startup does not source CachyOS configuration. Other Linux distributions need testing; no automatic package installation or default-shell changes are performed. Kitty supplies the image protocol. macOS and Windows are not tested.

## Install

Clone or download this repository, then run from its directory:

```sh
python3 install.py --dry-run
python3 install.py
```

The installer copies the curated `files/` tree into your home, expands home-path placeholders, backs up every existing file it replaces, and appends a marked include block to Kitty's existing config. Your general Fish `config.fish`, main Fastfetch config and main btop config are preserved. Installed Fish prompt/title functions replace same-name functions, with backups. A Fish `conf.d` snippet enables greetings inside Kitty. If your own `config.fish` redefines `fish_greeting` later, remove that conflicting definition or call `bankai-greeting` from it.

Defaults are character-balanced shuffle, all portraits, auto layout and mixed art. Existing values for these four preferences are retained. Existing favorites and history are never bundled or replaced. The theme installs to `~/.config` and `~/.local` and currently expects those locations even when `XDG_CONFIG_HOME` differs. History/deck state honors `XDG_STATE_HOME`. Symlink destinations are rejected; inspect `files/` and install manually if you use a symlink-based dotfile manager.

Open a new Kitty window, use Fish (`fish` if it is not your default shell), then run:

```fish
bankai-doctor
bankai-settings
```

The startup adds `~/.local/bin` to Fish's PATH. The package does not change your login shell or launch other terminals with Fish.

## Daily commands

```fish
bankai-art mixed                 # color | manga | mixed
bankai-pick                      # visual portrait picker
bankai-pick --session urahara    # pin a character in this shell
bankai-pick --session reset      # follow saved settings
bankai-group new-arrivals        # seven recent additions
bankai-group quincy              # five Quincy portraits
bankai-group all                 # full roster
bankai-shuffle character         # equal character turns
bankai-favorites                 # edit favorites with previews
bankai-history                   # recent editions and exact replay
bankai-history list
bankai-history 3                 # replay entry 3 once
bankai-layout compact            # auto | compact | full | off
bankai-greeting                  # show next greeting now
bankai-monitor                  # character-matched btop
bankai-backup                    # snapshot the current theme
```

Group/art changes apply at the next greeting. `bankai-pick random` resumes the current shuffle pool after a fixed selection. History starts with the first successful greeting and retains 50 entries. Settings also offer favorites, shuffle style, layout, snapshots and diagnostics.

## Uninstall and restore

```sh
python3 install.py uninstall --dry-run
python3 install.py uninstall
```

Uninstall restores replaced originals and removes files added by this installer, if they still match the installed version. Files edited since installation are retained and reported, with their backups and receipt kept for manual restoration. If only the main Kitty config has changed, uninstall removes its managed block while preserving other edits. Runtime state, favorites, history and snapshots are retained. The installation receipt and backups live in `~/.local/state/bleach-kitty-install`. Uninstall before reinstalling this package.

`bankai-backup restore` is a separate full-theme snapshot tool and may replace files recorded in the selected snapshot; it saves a new snapshot of current settings first. Installer backups are separate from these theme snapshots.

## Repository and validation

`files/` is the installable payload; `MANIFEST.json` records its SHA-256 hashes. `docs/prompts/` preserves generation prompt records. Run the isolated installer checks with:

```sh
python3 -m unittest discover -s tests -v
```

The installer can target an isolated directory via `--home /absolute/test/home`. That option is for staging/testing; desktop launchers and config references are expanded for that directory. Validation on the original setup covered all portraits/palettes, Fish/Kitty configuration, full shuffle cycles, groups and exact-edition replay. No real desktop session is launched by the automated installer tests.

## Publishing to GitHub

This directory is the repository root. Create an empty GitHub repository, then follow its “push an existing repository” instructions from here. No remote is preconfigured. The artwork is committed as regular PNG files; every individual file is below GitHub's 100 MiB limit. The complete payload is about 180 MiB, so initial cloning is substantial. The gallery HTML is intended to be opened locally; GitHub displays its source, while the README images render directly.

## License and artwork

Code and theme configuration are under the [MIT license](LICENSE). Bleach names, characters and associated rights belong to their respective rights holders. Artwork is unofficial AI-generated fan art and is excluded from the code license; see [ARTWORK.md](docs/ARTWORK.md). This project is not affiliated with or endorsed by Bleach's rights holders.
