# Changes

## Unreleased

- Match the login screen to the chosen desktop preset using eight full wallpaper scenes converted to black-and-white manga. Preserve the existing login layout and controls.
- Add optional one-time automatic matching setup for either edition, with a systemd path watcher, fixed preset validation, and restore/removal. App previews show the selected scene before activation.

- Add the optional Ichigo manga SDDM login theme, with preview, separate administrator activation, update, restore and exact standalone-install migration.
- Bundle the theme and helper with both desktop editions and all three release archives. Both apps offer a preview and copyable install/restore commands.
- Keep shared login assets while either desktop edition still owns them. Preserve edited system theme files by refusing updates or restores until edits are resolved.
- Always use Ichigo for the Plymouth boot splash; remove the Hollow-mask option and its assets. Preserve the existing internal theme name for upgrades.
- Keep Rust tray startup quiet, including repeated tray launches and the minimized fallback when the system tray is unavailable.
- Check login rendering in CI and staged login install/restore in extracted release packages.

Live SDDM authentication, real boot behavior, and KDE login/session behavior still require testing on a desktop. Per-user autostart choices and the development machine's 20-second login-window minimizer are not release defaults.
