# Artwork and provenance

[Browse the color and manga gallery](GALLERY.md)

The payload contains 46 color portraits and 46 matching manga portraits: 36 characters including alternate forms. All are unofficial AI-generated Bleach fan art. The manga editions use black-and-white ink, screentones and restrained character accents. No official manga pages or anime screenshots are included as artwork assets.

Artwork was produced during development using the built-in imagegen tool. The manga prompt records and the roster expansions are retained under [prompts](prompts/). They document prompts, references and output hashes where recorded. Initial color-generation prompts and the first Urahara manga prompt were not fully preserved in the available records; the repository does not invent provenance for those earlier assets. Local reference paths in these historical records have been normalized to `~/`; they describe the development setup, not installer destinations. Output files are now under `files/.config/fastfetch/portraits/` and `files/.config/fastfetch/manga/`.

The code's MIT license does not grant rights in Bleach characters, names, trademarks, or the character artwork. No ownership of third-party Bleach intellectual property or endorsement is claimed. Review these separate artwork terms and your intended use before redistribution. No blanket commercial-use license for the artwork is provided by this repository.

Nemu Kurotsuchi, Askin Nakk Le Vaar, Lille Barro and Yachiru Kusajishi were added on 2026-10-20 with matching color and manga portraits. [Exact prompts, references and output hashes](prompts/additions-20261020/PROMPTS.json) are preserved for all eight new assets.

## Login and boot artwork

The [manga login screen](../login/README.md) includes twelve black-and-white manga scene conversions of the full desktop wallpapers. [Exact prompt, source references, dimensions and hashes](../login/ARTWORK.json) are preserved. The Ichigo desktop scene is now `ichigo-desktop-v5.png`, with a forward-facing two-handed sword-guard pose and a locally retouched Zangetsu hilt and chain. Its matching monochrome login scene uses the same pose and was converted locally from the desktop image. Prompts, conversion details and hashes are recorded in [the TYBW expansion record](prompts/tybw-expansion-20261020/PROMPTS.json). The TYBW expansion also adds four backgrounds, corrects Yamamoto and adds separate True Shikai Ichigo and Bankai Kenpachi terminal portraits. The original Dangai portrait asset remains for migration compatibility. The paper layout, ink borders and lettering are drawn by QML; `login/preview.png` uses dummy login data. These unofficial fan-art scenes follow the same separate artwork terms above.

The [Ichigo boot splash](../boot/README.md) has its own [asset and prompt record](../boot/ARTWORK.json). Its character cutout is also excluded from the code MIT license. Aura, particle and loading-bar assets are generated from code-native geometry. Hollow-mask boot assets have been removed; the current splash always uses Ichigo.

## Rust application icon

The Substitute Soul Reaper badge in `desktop/rust/assets/bleach-tray.svg` is original SVG geometry authored for this project: a beveled ivory badge with a dark skull emblem, four diagonal spokes and a character-colored accent rivet. It replaces the earlier Hollow crest. [Launcher and tray size preview](screenshots/rust-icon.png). The design is unofficial Bleach fan art; no downloaded SVG or bitmap is embedded. Shape references were reviewed through [a badge replica photograph](https://theanimemerchant.com/products/bleach-substitute-soul-reaper-badge-replica) and [a badge model preview](https://sketchfab.com/3d-models/substitute-shinigami-badge-d9931ec2ae8d431d81b3890a2e525a2f).

The companion icons use original SVG geometry too: a black blade and orange slash for the terminal, a blue Quincy-inspired cross and pulse for the monitor, and layered ivory archive boxes for snapshots. [Icon family and small-size preview](screenshots/rust-icon-family.png). Terminal and monitor launchers have distinct icons; Rust embeds the same designs in its menus and navigation.
