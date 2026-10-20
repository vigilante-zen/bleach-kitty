# Bankai Manga login screen

The existing paper background, ink borders, lettering and controls now frame a **manga version of the complete selected desktop wallpaper scene**. Eight bundled scenes cover Ichigo, Rukia, Quincy/Uryu, TYBW, Urahara, Byakuya, Yamamoto and Ulquiorra. Color desktop wallpapers and terminal portraits are unchanged. [Artwork prompts, references and hashes](ARTWORK.json) · [Artwork terms](../docs/ARTWORK.md).

![Ichigo login preview](preview.png)

## Preview

From the repository or extracted package root, preview the currently selected character in the real greeter without logging out:

```bash
python3 login/greeter_preview.py
```

SDDM with Qt 6 is required. Login and power actions are disabled in test mode. Both Bankai apps provide the same preview through **Login screen setup**. No administrator access is needed to preview.

`python3 login/preview.py --preset rukia --output /tmp/rukia-login.png` renders a PNG using PySide6 and dummy login data. Without options it renders the checked-in Ichigo preview. The full scene fits inside the existing frame, with dark space above and below wide artwork.

## One-time automatic matching setup

Both desktop installers bundle the scenes and helper. After installing or updating the chosen Bankai edition, run this from your normal desktop account:

```bash
sudo python3 ~/.local/share/bleach-desktop/install-login.py install
```

Or, from the repository/package root:

```bash
sudo python3 login/install.py install
```

When invoked with sudo, setup follows the sudo caller's desktop preset. A root shell can select an account explicitly with `--follow-user USERNAME`. Re-running setup upgrades an existing installation and preserves its followed account when no new one is supplied. An exact original standalone Ichigo theme can be adopted; edited or unrelated files are left untouched.

After setup, selecting a background in either Bankai app changes the scene for the **next login screen**, without another sudo prompt. It also follows preset changes from the command line and snapshot restores. The TYBW preset uses the manga edition of the full ensemble wallpaper. The currently displayed greeter is not live-reloaded.

Matching reads `~/.local/share/bleach-desktop/current`. A systemd path unit starts a short-lived root-owned helper when that marker changes. Only eight recognized preset names are accepted; the helper never executes code or loads artwork from the user's home. It selects preinstalled scene files using SDDM's `theme.conf.user`. Missing, invalid, oversized or linked markers keep the previous scene. An enabled one-shot service refreshes the selection before the display manager at boot; an unavailable/encrypted home retains the last saved scene.

The login screen is machine-wide: one chosen desktop account controls its scene, even on a multi-user machine. This follows the desktop background preset, independently of terminal portrait rotation or favorites.

## Fixed scene and restore

To stop automatic matching and keep the Ichigo scene:

```bash
sudo python3 ~/.local/share/bleach-desktop/install-login.py install --static
```

To restore the previous SDDM selection and remove the managed theme and matching service:

```bash
sudo python3 ~/.local/share/bleach-desktop/install-login.py restore
```

From the repository/package, use `sudo python3 login/install.py restore`. Restore checks managed file hashes before removing files. The generated character selection is allowed to change through the helper; other local edits block update/removal. Restore before uninstalling the final desktop edition if you need its installed helper.

## Files and verification

Setup adds the separate `/etc/sddm.conf.d/zz-bankai-manga.conf` override and `/usr/share/sddm/themes/bankai-manga/` theme. Automatic matching also installs `bankai-login-sync.path` and `bankai-login-sync.service` under `/etc/systemd/system/`. The receipt and followed account are stored under `/var/lib/bankai-login/`. Existing SDDM themes and configuration remain intact; a later-precedence override or `/etc/sddm.conf` may still take priority. No display-manager restart or logout is performed.

Use `--dry-run` to inspect changes. Use `--root /absolute/staging/root` for isolated installation tests; staging never calls the live systemd manager. Tests cover both edition marker-write patterns, preset validation, exact legacy migration, updates, edited-file protection and restore. Real authentication, systemd path activation, boot ordering and multi-monitor behavior still require testing on the login machine.

```bash
systemctl status bankai-login-sync.path
journalctl -u bankai-login-sync.service
```

References: [SDDM theme configuration](https://github.com/sddm/sddm/wiki/Theming), [systemd path units](https://www.freedesktop.org/software/systemd/man/latest/systemd.path.html).
