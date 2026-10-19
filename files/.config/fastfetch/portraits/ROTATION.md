# Portrait rotation

Random mode uses a persistent shuffle deck: each available portrait appears once per cycle. Deck state is shared across Kitty tabs, and cycle boundaries avoid immediate repeats when there is more than one portrait. A portrait selected with `bankai-pick <name>` stays fixed.

- `bankai-pick random`: shuffle the currently active pool.
- `bankai-favorites`: open the preview picker; Tab marks portraits, Enter replaces and activates favorites, Esc cancels.
- `bankai-favorites add urahara rukia-bankai`: add favorites and activate their rotation.
- `bankai-favorites remove urahara`: remove a favorite.
- `bankai-favorites list`: list saved favorites.
- `bankai-favorites status`: show the active pool.
- `bankai-favorites all`: rotate everyone, keeping saved favorites.
- `bankai-favorites use`: reactivate saved favorites.

Changes take effect at the next greeting. Open a new Kitty tab, or run `bankai-greeting`. An empty or unavailable favorites pool falls back to all portraits. Pool changes start a fresh cycle.

Favorites are saved in `~/.config/fastfetch/portrait-favorites.json`. The deck is stored under `$XDG_STATE_HOME/bleach` (default `~/.local/state/bleach`).

## Character groups

`bankai-group` shows the active rotation and available groups. Choose with `bankai-group soul-reapers`, `bankai-group arrancars`, `bankai-group quincy`, `bankai-group human-world`, or `bankai-group ichigo`. Use `bankai-group all` for everyone. Human World is a themed group and overlaps other groups.

Group selection activates shuffle mode and preserves saved favorites. `bankai-favorites use` switches back to favorites. Changing the pool starts a fresh deck. A portrait fixed with `bankai-pick <name>` stays fixed until a group, favorites rotation, or random mode is selected.

## Saved greeting layout

`bankai-layout auto|compact|full|off` saves the layout for future greetings. With no argument it reports the preference. Auto adapts to window size. Off hides the greeting without consuming the deck. `bankai-greeting --compact` and `bankai-greeting --full` preview a layout once, including while the saved preference is off. Settings are stored in `~/.config/fastfetch/greeting-mode`.

## Settings menu

Run `bankai-settings` in Kitty for portraits with previews, character groups, favorites, saved greeting layouts, a one-time compact greeting preview, and snapshot creation/verification/restoration. Enter opens an item and Esc returns or exits. The header shows the selected portrait, current rotation, saved favorites count and greeting layout. Preview greeting exits the menu so the greeting stays visible.

## Character-balanced shuffle

`bankai-shuffle character` gives each character one turn per cycle, treating the six Ichigo portraits as forms of one character. Ichigo's available forms use a separate shuffle deck so every form appears before repeating. With the full roster this is 32 character turns per cycle. Favorites and groups limit the eligible portraits before balancing.

`bankai-shuffle portrait` restores the original every-image-once deck (40 images in the full roster). `bankai-shuffle` reports the saved style. Both styles avoid immediate repeats at cycle boundaries where possible and persist across tabs. The style is also available under Shuffle style in `bankai-settings`. Fixed portraits remain fixed; choose `bankai-pick random` to resume rotation. The default style remains portrait.

## Kitty settings shortcut

Press Ctrl+Shift+F12 to open `bankai-settings` in a Kitty overlay over the current terminal. Esc exits the top-level menu and closes the overlay. Existing Kitty windows can load the shortcut with Ctrl+Shift+F5; new windows load it automatically.

## Setup checks

Run `bankai-doctor`, or choose Check setup in `bankai-settings`, to validate required tools, portrait PNG headers, matching full/compact greeting and btop palettes, Fish syntax and prompt colors, Kitty configuration, and saved layout/shuffle/portrait choices. The command reports failures and exits with a nonzero status without changing theme settings.

## Bankai variants

Urahara, Renji, and Hitsugaya each have base and Bankai portraits. Select `urahara-bankai`, `renji-bankai`, or `hitsugaya-bankai` in the picker. Portrait shuffle rotates all 40 images. Character shuffle gives the 32 characters equal turns, with separate form decks for Ichigo, Urahara, Renji, and Hitsugaya. Favorites can include either form or both.

## Readable portrait names

Portrait and favorites pickers show names such as Urahara · Bankai and Hitsugaya · Adult Bankai, sorted with related forms together. Search by character or form. Direct commands and `bankai-pick --list` continue to use the original identifiers, such as `urahara-bankai`.

## Editing existing favorites

`bankai-favorites` starts with saved favorites checked. Tab toggles the highlighted portrait, Alt+A checks everyone, and Alt+D unchecks everyone. Enter saves only the marked portraits; an empty marked list clears saved favorites and returns to the non-favorites rotation. Esc cancels without changing the saved list. `bankai-favorites clear` clears saved favorites directly; `bankai-favorites all` keeps them saved while rotating everyone.

## Session-only portraits

Run `bankai-pick --session urahara` in the shell you want to pin. `bankai-pick --session` opens a picker for that shell. `bankai-pick --session random` temporarily shuffles the active pool even if the saved default is fixed. `bankai-pick --session reset` removes the override and follows saved defaults. The override is not exported to new shells, saved to disk, or shared with other Kitty tabs. A regular `bankai-pick <name>` saves the global preference and clears the current shell override. A saved off layout still hides greetings; use `bankai-greeting --compact` to preview.

## Bookmark the current portrait

`bankai-favorites toggle` adds or removes the portrait active in this shell. `bankai-favorites toggle urahara` toggles a named portrait. Bookmarking preserves the current group, fixed/session selection, shuffle style and deck position; it does not activate favorites mode. If favorites mode is already active, the changed list becomes its pool, falling back to the non-favorites rotation when emptied. `bankai-settings` shows Favorite current portrait or Remove current favorite when its shell has an active portrait.

## Redesigned greeting and art editions

The redesigned full greeting uses a bold character heading, system identity, hardware and session sections, aligned labels and a short settings hint. The compact greeting shows system, uptime, memory and terminal. Auto selects the full view at 104+ columns and 28+ rows; smaller windows get a compact layout with a scaled or stacked portrait.

`bankai-art color|manga|mixed` saves the art edition. Mixed randomly selects an available art edition after choosing the character, so art editions do not change shuffle fairness. All 40 portraits now have matching color and manga editions (80 images across 32 characters). Manga uses monochrome ink and screentones with a restrained character accent. Missing manga falls back to the original color image. The selected character, prompt, cursor, favorites and monitor palette remain tied to the same character. The Portrait art item in `bankai-settings` controls this too. Color and manga images live in separate folders.

`bankai-manga-preview` shows Urahara's redesigned compact manga greeting once without changing preferences or consuming the shuffle deck. The local color/manga layout comparison is `~/.config/fastfetch/previews/redesign.html`.

Compare every edition side by side in `~/.config/fastfetch/previews/manga-roster.html`. The additional 32 manga editions were created with the built-in imagegen tool; exact prompts, reference hashes and output hashes are saved in `~/.config/fastfetch/manga/EDITION-PROMPTS.json`. Original color artwork is preserved.

## Edition labels and recent art

Greetings show a muted COLOR or MANGA label beside the character heading. Only successfully rendered greetings are added to the last 50 entries in `$XDG_STATE_HOME/bleach/art-history.json` (default `~/.local/state/bleach`). History is shared across Kitty tabs and writes are locked.

Run `bankai-history`, or choose Recent art in `bankai-settings`, to browse with exact-edition previews. Enter shows the selected character and edition once in the compact layout. `bankai-history list` prints numbered entries; `bankai-history 3` replays entry 3. Replay preserves saved portrait/art choices, session selection, favorites and shuffle position, while updating the visible character accents. Replays also appear in history. History starts with your next greeting.

## Additional characters

Coyote Starrk (`starrk`), Tier Harribel (`harribel`), Shuhei Hisagi (`hisagi`) and Sajin Komamura (`komamura`) each have color and manga editions, matching greeting/prompt/monitor palettes and history support. Starrk and Harribel join Arrancars; Hisagi and Komamura join Soul Reapers. The roster now has 40 portraits, 32 characters and 80 art editions. The addition prompts are in `~/.config/fastfetch/additions-20261019/PROMPTS.json`.

## New arrivals and Quincy expansion

`bankai-group new-arrivals` rotates Starrk, Harribel, Hisagi, Komamura, Jugram, Bazz-B and Bambietta. This group also appears in settings and tab completion. Mixed mode continues to select color or manga after selecting the portrait. `bankai-group all` restores the full roster.

Jugram Haschwalth (`jugram`), Bazz-B (`bazz-b`) and Bambietta Basterbine (`bambietta`) join the Quincy group with matching color/manga art, greetings, prompt/monitor accents and history support. The complete roster has 40 portraits, 32 characters and 80 art editions. Prompts: `~/.config/fastfetch/quincy-additions-20261019/PROMPTS.json`.
