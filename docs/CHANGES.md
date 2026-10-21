# Changes

## Unreleased

- Make snapshot restore transactional in both desktop editions. Stage and verify snapshot bytes before applying them, then restore replaced or deleted files with their original permissions if a later operation fails.
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
