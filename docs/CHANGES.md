# Changes

## Unreleased

- Show and expose a live terminal character result count for search and faction filters; politely announce updated counts after typing pauses on Qt 6.8+, and describe card actions and arrow-key navigation to screen readers.
- Scale Rust brand, section labels and headings with KDE's configured UI font; reflow backup actions and the terminal picker on resize, and fit preview dialogs to screen space, verified by the native smoke test.
- Add screen-reader context for Rust navigation, saved custom presets, terminal-follow and art-style options, autostart, and the activity log; verify the Qt-exposed labels in the native smoke test.
- Add an integrity-checked restore preview to the Rust Backups page, listing every saved file to restore and every setting to remove before the user confirms an actual restore.
- Widen the Rust sidebar enough to show full navigation labels and keyboard shortcuts; tighten its internal spacing so labels still fit on narrower displays.
- Add case-insensitive search to the Rust saved-snapshot list, with a helpful empty-results message and disabled restore actions when no snapshots match.
- Add screen-reader names and live character descriptions to the Rust appearance and terminal artwork previews, and accessible names/descriptions to terminal search, filters, and Random. Extend the native UI smoke test to verify those descriptions.
- Fit the Rust window's minimum size to the available display, let the sidebar contract on narrow screens, and make the backup controls scroll on short displays.
- Add screen-reader context to the Rust login-shuffle editor and snapshot controls, including filtered-list actions, retention behavior, restore review, and cleanup preview.
- Add a high-contrast focus border for Rust buttons, pickers, search fields, checkboxes, and lists so keyboard focus remains visible across the dark theme.
- Verify screen-reader names and descriptions through Qt's accessibility interfaces in the native UI smoke test, including descriptions that change with the selected character.
- Make snapshot restore transactional in both desktop editions. Stage and verify snapshot bytes before applying them, then restore replaced or deleted files with their original permissions if a later operation fails. Require the manifest version to be an integer in both editions.
- Limit snapshot manifests to 16 MiB consistently across Rust verification, Python backup/restore and Python snapshot scanning; prevent either edition from creating an oversized manifest. Reject oversized manifests before parsing.
- Coordinate Python and Rust snapshot operations through the shared lock. Keep the Python control center responsive during another edition's snapshot operation, and reject malformed absent-file metadata, symlinked paths, and special files before verification, protection or cleanup. Both editions now use one shared restore-path policy, so cleanup cannot mark a path eligible that Rust would refuse to restore; installers ship that policy with Python builds.
- Reject symlinked desktop state, lock and socket paths during single-instance startup in both editions, so IPC setup cannot be redirected through a symlink.
- Reject dangling symlinks in configured Python snapshot paths rather than recording them as absent. Assert that subprocess and extracted-package snapshot checks include and restore KDE configuration alongside terminal settings.
- Check Python snapshot boundary directories for symlinks and reject paths that escape their allowed root, matching Rust's path checks.
- Exercise snapshot creation and restore from extracted Python and prebuilt Rust release packages on pushes, pull requests and releases, including absent-file cleanup and retention of the pre-restore backup.
- Apply preset changes in both desktop editions as transactions across desktop configuration and saved-state markers; roll back earlier writes if a later write fails. Custom preset application now snapshots the previous appearance choices, then commits the preset and replacement choices together so failed applies leave both unchanged.
- Serialize Python custom-preset edits with Rust and snapshot operations to prevent concurrent updates from being lost. Refresh custom presets in both editions after external changes while preserving selection, and offer to restore malformed appearance settings after backing up the unreadable file. Show the exact characters eligible for terminal Random, use unbiased random selection for login shuffle, and refresh the Backups page after external changes. Reject stale appearance saves across editions, keep the Rust window usable when saved presets are malformed by showing an error and allowing reload after repair, and reject symlinked current-preset state.
- Run Clippy with warnings denied in Rust CI and document the lint command in the Rust install and development guides.
- Improve the Rust terminal character picker with a searchable thumbnail grid, faction/form filters, recent and favorite selections, keyboard navigation, clearer empty states and an always-available random choice.
- Add Aizen, Grimmjow, Yoruichi, Gin and Orihime as desktop presets, with matching Color and Manga wallpapers and login scenes.
- Refine Aizen's Color and Manga sword artwork to depict Kyōka Suigetsu; make ultrawide art prompts name each character's Zanpakutō/release. Grimmjow's scene uses Pantera; Yoruichi's uses Shunkō without a sword. Gin's uses the extended Shinso; Orihime's uses Santen Kesshun without a Zanpakutō.
- Correct Ichigo's wallpaper to his Royal Palace True Shikai design and Yamamoto's TYBW arm/weapon design. Keep Ulquiorra as a legacy option.
- Add TYBW Ichigo and Bankai Kenpachi color/manga terminal portraits, character accents and a TYBW forms group: 46 portraits / 92 editions, still 36 characters.
- Add shared appearance controls in both apps for color/manga backgrounds, custom accents, fixed/following login scenes, and optional login shuffle with a character pool.
- Save, preview, apply and delete named custom combinations of the current wallpaper, accent and login-scene choices in both apps.
- Add terminal installer updates that retain preferences, original backups and edited files, and deliver new artwork through either desktop installer.
- Replace the Ichigo desktop/lock-screen wallpaper and monochrome login scene with a weapon-free standing pose. Make Python wallpaper selection honor the shared preset catalog, matching Rust for versioned asset filenames.
- Add full and compact Fastfetch layouts for TYBW Ichigo and Bankai Kenpachi. Refine Fastfetch key colors and btop highlight colors for TYBW Ichigo, Askin, Lille, Nemu and Yachiru.

- Match the login screen to the chosen desktop preset using full wallpaper scenes converted to black-and-white manga. Preserve the existing login layout and controls.
- Add optional one-time automatic matching setup for either edition, with a systemd path watcher, fixed preset validation, and restore/removal. App previews show the selected scene before activation.

- Add the optional Ichigo manga SDDM login theme, with preview, separate administrator activation, update, restore and exact standalone-install migration.
- Bundle the theme and helper with both desktop editions and all three release archives. Both apps offer a preview and copyable install/restore commands.
- Keep shared login assets while either desktop edition still owns them. Preserve edited system theme files by refusing updates or restores until edits are resolved.
- Always use Ichigo for the Plymouth boot splash; remove the Hollow-mask option and its assets. Preserve the existing internal theme name for upgrades.
- Keep Rust tray startup quiet, including repeated tray launches and the minimized fallback when the system tray is unavailable.
- Check login rendering in CI and staged login install/restore in extracted release packages.

Live SDDM authentication, real boot behavior, and KDE login/session behavior still require testing on a desktop. Per-user autostart choices and the development machine's 20-second login-window minimizer are not release defaults.
