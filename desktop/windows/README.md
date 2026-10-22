# Bankai for Windows — initial WinUI 3 preview

A separate C# / WinUI 3 interface for Bankai. This first implementation loads the
existing shared preset catalog, filters characters by name or description, and
previews their wallpaper. It does not modify desktop settings.

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

This project was authored on Linux without a .NET SDK. Compilation, launch,
keyboard navigation, screen-reader behavior, filtering and image decoding still
need verification on Windows; the CI workflow has not been run from this session.

## Next implementation stages

1. Verify the initial app on Windows, including resizing, keyboard navigation,
   empty searches, missing artwork and Narrator.
2. Add a Windows platform service for wallpaper application with explicit Apply
   and recoverable previous settings. Keep Windows state under
   `%LOCALAPPDATA%\Bankai`; Linux snapshot manifests are not Windows backups.
3. Add Windows Terminal appearance settings, with previews and backup/restore.
4. Add single-instance activation, tray controls and optional login startup.
5. Add Windows-specific snapshot review and restore, then signed distribution.

The existing Rust implementation depends on Qt and KDE. It is not currently a
portable library or connected to this interface. Extract pure configuration and
snapshot logic behind a versioned boundary when Windows needs it; never invoke
Linux desktop commands or reuse Linux restore paths on Windows.

Project structure follows Microsoft's [unpackaged WinUI sample](https://github.com/microsoft/winappCli/tree/main/samples/winui-unpackaged-app).
