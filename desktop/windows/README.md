# Bankai for Windows — WinUI 3 preview

A separate C# / WinUI 3 interface for Bankai. This first implementation loads the
existing shared preset catalog, filters characters by name or description, previews
their wallpaper, and applies the selected wallpaper to all connected monitors.

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
also runs isolated wallpaper recovery checks, launches the published interface,
verifies initial preview loading and search behavior, and creates a portable ZIP
with its SHA-256 checksum. These checks do not change the runner's real wallpaper.
Wallpaper application, multi-monitor recovery, keyboard navigation and Narrator
still need testing on a real Windows desktop. No installer, signing or automatic
updates are included yet.

Run the wallpaper recovery checks independently (no Windows desktop required):

```powershell
dotnet run --project desktop/windows/Checks/Bankai.Windows.Checks.csproj -c Release
```

## Next implementation stages

1. Verify live wallpaper application and restore on Windows, including multiple
   monitors, resizing, keyboard navigation, missing artwork and Narrator.
2. Add Windows Terminal appearance settings, with previews and backup/restore.
3. Add single-instance activation, tray controls and optional login startup.
4. Add Windows-specific snapshot review and restore, then signed distribution.

The existing Rust implementation depends on Qt and KDE. It is not currently a
portable library or connected to this interface. Extract pure configuration and
snapshot logic behind a versioned boundary when Windows needs it; never invoke
Linux desktop commands or reuse Linux restore paths on Windows.

Project structure follows Microsoft's [unpackaged WinUI sample](https://github.com/microsoft/winappCli/tree/main/samples/winui-unpackaged-app).
