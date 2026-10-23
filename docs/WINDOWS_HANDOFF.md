# Continue Bankai on another computer

All Windows source, shared artwork and project notes are in
https://github.com/vigilante-zen/bleach-kitty on branch `main`.

## Get the project

Install Git, then open a terminal in the folder where you want the project:

```powershell
git clone https://github.com/vigilante-zen/bleach-kitty.git
cd bleach-kitty
```

If this computer already has a checkout, open that checkout and inspect
`git status` before updating it with `git pull --ff-only`. Preserve any local work.

Read `PROJECT_CHECKPOINT.md` and `desktop/windows/README.md`. For Windows builds,
install the .NET 10 SDK, Windows SDK and Visual Studio's WinUI development tools.
Then run from the repository root:

```powershell
dotnet run --project desktop/windows/Checks/Bankai.Windows.Checks.csproj -c Release
dotnet publish desktop/windows/Bankai.Windows.csproj -c Release -p:Platform=x64 -o windows-preview
.\windows-preview\Bankai.Windows.exe
```

The recovery checks also run on Linux with the .NET 10 SDK. Building and launching
WinUI needs Windows; the GitHub Windows workflow is available for remote builds.
Testing the portable download alone does not require installing development tools.

## Where work stands

- C# / WinUI 3, Windows x64, unpackaged self-contained portable preview.
- Eighteen shared presets, character search and wallpaper previews.
- Explicit wallpaper application and previous-background recovery, with Windows
  state under `%LOCALAPPDATA%\Bankai`.
- Windows Terminal installation/profile selection, character color previews,
  comment-preserving Apply and exact-byte Restore. Each installation has separate
  recovery data; changed settings are detected before Apply or Restore.
- Eleven wallpaper and sixteen Terminal recovery checks pass on Linux and Windows.
  The Linux Terminal checks include symlink rejection; Windows checks include a
  locked-settings replacement failure and preservation of earlier restore data.
- Published-app checks exercise wallpaper previews/search and Terminal Apply/Restore
  using disposable settings, without changing the runner's real preferences.
- Current implementation source: `23f601c`.
- Successful build and downloadable artifact:
  https://github.com/vigilante-zen/bleach-kitty/actions/runs/39882854418
- SHA-256 for that run's `bankai-windows-x64-preview.zip`:
  `34a42fd7e824e2b175d7e432d0af3d6ddcb3f050b11cb097fe79e8496cd6a2cb`.
  Later builds are available from the Windows edition workflow; each includes
  its own SHA-256 sidecar.

Start with interactive testing of Apply/Restore on a real Windows desktop,
including multiple monitors, keyboard use and Narrator. Automated recovery checks
use a fake wallpaper backend and have not verified real wallpaper changes. Test
Terminal's live reload and profile overrides interactively too. Terminal colors
are implemented; artwork inside the shell and terminal launchers remain future
extensions. Tray controls,
single-instance activation, optional startup, a backup browser and installer/signing
remain future work.

Do not remove `EnableMsixTooling` or the explicit `resources.pri` filename from the
project: the launch check caught missing resources in earlier publish attempts.

The Linux edition remains a separate supported implementation. The Linux release
is still pending publication; it is separate from this Windows development preview.

## Resume prompt for a new coding session

> Continue the Windows edition of Bankai in this repository. Read
> PROJECT_CHECKPOINT.md, docs/WINDOWS_HANDOFF.md and desktop/windows/README.md
> first. Work in desktop/windows using C# and WinUI 3, preserving the Linux
> editions and shared artwork. The current preview has searchable character
> wallpapers, wallpaper Apply and Restore, plus Windows Terminal color previews,
> profile selection, comment-preserving settings updates and independent recovery.
> Start by checking the worktree and validating the preview on Windows, then
> continue with the next requested feature. Preserve any local screenshots.

The original computer's untracked `artifacts/` screenshots, generated `dist/`
downloads and installed preferences/backups are not in Git. Copy those separately
only if you want them on the other computer. No local files are needed to rebuild
the Windows preview from the repository.
