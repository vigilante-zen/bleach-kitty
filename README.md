# Bankai · Bleach desktop and terminal

A character-driven Bleach theme for Kitty, Fish, Fastfetch and btop. Includes **36 characters, 46 portraits and 92 art editions**, with matching shell, cursor, greeting and monitor accents.

[Browse all color and manga artwork](docs/GALLERY.md) · [Full command guide](files/.config/fastfetch/portraits/ROTATION.md) · [Artwork provenance and prompts](docs/ARTWORK.md) · [Change log](docs/CHANGES.md)

| Color | Manga |
| --- | --- |
| ![Urahara in color](files/.config/fastfetch/portraits/urahara.png) | ![Urahara in manga ink](files/.config/fastfetch/manga/urahara.png) |

## Choose your edition

| Rust edition · default | Python edition · alternative |
| --- | --- |
| Compiled Rust core + Qt desktop app | Original Python + PySide6 desktop app |
| Live portrait previews and desktop matching | No compilation step |
| **[Install Rust →](desktop/rust/INSTALL.md)** | [Install Python →](desktop/python/INSTALL.md) |
| [Rust source and details](desktop/rust/README.md) | [Python source and details](desktop/python/README.md) |

[Download edition packages](https://github.com/vigilante-zen/bleach-kitty/releases) · [See app screenshots](desktop/README.md#screenshots)

Rust is the default desktop edition. Run `python3 desktop/install.py` from the repository root to install it; the Python edition remains available through its separate installer. Each edition has backups, launcher creation, updates and uninstall support. [Compare editions or switch later](desktop/README.md).

For the terminal theme on its own, follow [Terminal theme installation](#install) below.

## Optional animated boot splash

[Preview and install the Bleach boot theme](boot/README.md): an Ichigo silhouette with flowing reiatsu. This is a separate optional system theme, with installation and restore steps.

## Optional manga login screen

Both desktop installers include the [matching manga-scene SDDM theme](login/README.md). Open **Login screen setup** in either Bankai app to preview the matching full manga wallpaper scene. One-time administrator setup lets it follow later background changes automatically; the same screen provides a restore command.

## Features

- Color, manga, or randomly mixed art editions.
- Persistent shuffle decks shared across Kitty tabs; equal turns per portrait or per character.
- Favorites, character groups, and session-only portrait selection.
- Responsive full/compact greetings, plus a saved off mode.
- Character-colored prompts, Git/status hints, cursor, window titles and btop themes.
- Dedicated full and compact Fastfetch layouts for TYBW Ichigo and Bankai Kenpachi, with matching character accents.
- Recent-art history with exact-edition previews and replay.
- Settings overlay on **Ctrl+Shift+F12**.
- Setup diagnostics and verified theme snapshots.

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

## Appearance options

Both Bankai apps provide **Appearance options** beside the background controls: choose Color or Manga for the desktop and lock screen, set a custom accent (or leave it empty for character colors), choose a fixed manga login scene or follow the background, and choose a character pool for optional shuffle at login. Save options, then Apply a preset to update wallpaper and accent. Login choices require the one-time system setup. Enable only one Bankai edition at login for shuffle. Terminal Color/Manga/Mixed and favorites remain separate.

Save your current character wallpaper, accent, and login-scene choices as a named custom preset from the appearance page. Saved combinations can be previewed, applied, or deleted in either edition.

There are seventeen desktop presets, including Aizen, Grimmjow, Yoruichi, Gin, Orihime, TYBW Renji, adult Bankai Hitsugaya, Bankai Kenpachi and Yhwach. The terminal roster also includes TYBW True Shikai Ichigo and Bankai Kenpachi as separate forms.

## Daily commands

```fish
bankai-art mixed                 # color | manga | mixed
bankai-pick                      # visual portrait picker
bankai-pick --session urahara    # pin a character in this shell
bankai-pick --session reset      # follow saved settings
bankai-group new-arrivals        # thirteen recent portraits
bankai-group tybw-forms          # TYBW forms and Yhwach
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

## Update

```bash
python3 install.py update --dry-run
python3 install.py update
```

Updates add new artwork and refresh unchanged managed files. Existing preferences, locally edited files and the original backups are retained. Both desktop installers run this update automatically for an existing terminal installation unless `--skip-theme` is supplied.

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

## GitHub repository

[Recent changes](docs/CHANGES.md) · [Release packaging and CI instructions](docs/RELEASING.md).

Both desktop editions live in this repository with separate install guides and source directories. Shared assets are stored once in `desktop/shared/`. The terminal payload remains in `files/`, with checksums in `MANIFEST.json`. GitHub's repository ZIP contains both source editions; follow only your chosen edition's setup guide.

The artwork is committed as regular PNG files, so cloning includes a substantial artwork download. The [portrait gallery](docs/GALLERY.md) renders directly on GitHub. The bundled HTML gallery under `files/.config/fastfetch/previews/` is for local browser viewing.

## License and artwork

Code and theme configuration are under the [MIT license](LICENSE). Bleach names, characters and associated rights belong to their respective rights holders. Artwork is unofficial AI-generated fan art and is excluded from the code license; see [ARTWORK.md](docs/ARTWORK.md). This project is not affiliated with or endorsed by Bleach's rights holders.
