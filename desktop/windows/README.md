# Bankai for Windows — WinUI 3 preview

A separate C# / WinUI 3 interface for Bankai. This first implementation loads the
existing shared preset catalog, filters characters by name or description, previews
their wallpaper, and applies the selected wallpaper to all connected monitors.
The Windows Terminal page previews and applies matching character color schemes
to a selected Terminal profile, with independent settings backup and restore.

## Use the portable preview

Download `bankai-windows-x64-preview` from a successful [Windows edition workflow
run](https://github.com/vigilante-zen/bleach-kitty/actions/workflows/windows.yml).
Extract the artifact, then extract `bankai-windows-x64-preview.zip`. Open the
`windows-preview` folder and run `Bankai.Windows.exe`. Keep all files together.
The output includes its .NET and Windows App SDK runtimes.

Select a character and click **Apply wallpaper**. Selecting or searching alone
does not change Windows. Apply saves copies of the previous wallpaper images,
per-monitor assignments, position and background color under
`%LOCALAPPDATA%\Bankai\WallpaperBackups` before changing the background. It also
keeps its own copy of the selected artwork, so moving the portable app does not
remove the wallpaper file.

**Restore previous wallpaper** restores the last saved background and saves the
one it replaces, allowing that restore to be undone. Failed changes attempt to
restore their saved starting state. Backups persist after the app closes and are
retained on disk; automatic cleanup and a full backup browser are not implemented.
Recovery data is specific to Windows and does not use Linux snapshots.

This first implementation supports static Picture and Solid color backgrounds.
Switch away from a Windows slideshow before applying or restoring. A restore
requires the original monitor set to be connected. Application and restore run on
a background STA thread; the window remains open until an operation finishes.

The catalog and wallpapers are linked from `desktop/shared` during build and
copied into the output. No second catalog or duplicate source artwork is needed.
The Linux installers and applications are unchanged.

## Windows Terminal colors

Open the **Windows Terminal** tab, choose an installation, profile and character,
then click **Apply terminal colors**. Stable, Preview, Canary and standard
unpackaged settings are detected when their settings files exist. Run Terminal
once and use **Refresh** if it has not created settings yet. Use **Choose settings
file** for other portable installations. Selecting or previewing never writes the
settings file.

The scheme uses Bankai's existing dark terminal palette with the selected
character's ANSI red/bright-red, cursor and selection accent. It is added as
`Bankai <Character>`. Choose a specific profile to change that profile alone, or
choose **Profile defaults** to affect profiles that inherit their scheme. Explicit
profile color overrides still take precedence. Fonts, shell commands, shortcuts,
background images, other profiles and unrelated schemes are preserved.

Settings use JSONC: existing comments, trailing commas, UTF-8 byte-order marks and
unrelated formatting are retained; the selected color-scheme value and new scheme
entries are the intended edits. A different existing scheme with the same Bankai
name is refused rather than overwritten. Settings must be valid UTF-8 JSONC,
without duplicate keys, and no larger than 8 MiB. Symlinks and directory junctions
in settings/backup paths are refused.

Each installation has separate recovery data under
`%LOCALAPPDATA%\Bankai\TerminalBackups`. Before a write, Bankai saves the exact
original bytes, records SHA-256 integrity information, checks that the loaded
settings have not changed, and atomically replaces the settings file.
**Restore previous terminal settings** recovers
those bytes and saves the settings it replaces, allowing the restore to be undone.
Backups remain on disk; automatic cleanup is not implemented.

If settings changed after preview, Refresh before applying. If they changed after
Bankai's last update, automatic restore stops to preserve those newer edits. The
original `.settings.json` backup remains in TerminalBackups for manual review and
selective recovery. Terminal normally reloads settings automatically; reopen a tab
if needed. See Microsoft's [color-scheme documentation](https://learn.microsoft.com/windows/terminal/customize-settings/color-schemes)
and [settings locations](https://learn.microsoft.com/windows/terminal/faq).

This stage changes Terminal colors. Character artwork inside the shell, profile
background images, terminal launchers and prompt installation remain separate work.

## Build on Windows

Use a Windows development machine with the .NET 10 SDK, the Windows SDK and
Visual Studio's WinUI application development tools. Initial target: Windows 10
version 2004 or later, x64.

```powershell
dotnet publish desktop/windows/Bankai.Windows.csproj -c Release -p:Platform=x64 -o windows-preview
.\windows-preview\Bankai.Windows.exe
```

Distribute the entire output directory. This is an unpackaged, self-contained
preview, not an MSIX installer or a single-file executable. It requests no
administrator privileges. The Windows edition workflow publishes the same output
as a downloadable CI artifact when its build succeeds.

The initial preview compiled successfully on a Windows GitHub runner. The workflow
also runs isolated wallpaper and Terminal recovery checks, launches the published
interface, verifies initial preview loading and search behavior, exercises Terminal
Apply/Restore against a disposable settings file, and creates a portable ZIP with
its SHA-256 checksum. These checks do not change the runner's real wallpaper or
Terminal settings. Live Terminal reload, wallpaper application, multi-monitor
recovery, keyboard navigation and Narrator
still need testing on a real Windows desktop. No installer, signing or automatic
updates are included yet.

Run the wallpaper and Terminal recovery checks independently (no Windows desktop required):

```powershell
dotnet run --project desktop/windows/Checks/Bankai.Windows.Checks.csproj -c Release
```

## Next implementation stages

1. Verify live wallpaper application and restore on Windows, including multiple
   monitors, resizing, keyboard navigation, missing artwork and Narrator.
2. Verify Terminal profile colors and reload on a real Windows installation, then
   extend terminal artwork and launch integrations.
3. Add single-instance activation, tray controls and optional login startup.
4. Add Windows-specific snapshot review and restore, then signed distribution.

The existing Rust implementation depends on Qt and KDE. It is not currently a
portable library or connected to this interface. Extract pure configuration and
snapshot logic behind a versioned boundary when Windows needs it; never invoke
Linux desktop commands or reuse Linux restore paths on Windows.

Project structure follows Microsoft's [unpackaged WinUI sample](https://github.com/microsoft/winappCli/tree/main/samples/winui-unpackaged-app).
