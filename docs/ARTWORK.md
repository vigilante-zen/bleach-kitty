# Artwork and provenance

[Browse the color and manga gallery](GALLERY.md)

The payload contains 46 color portraits and 46 matching manga portraits: 36 characters including alternate forms. All are unofficial AI-generated Bleach fan art. The manga editions use black-and-white ink, screentones and restrained character accents. No official manga pages or anime screenshots are included as artwork assets.

Artwork was produced during development using the built-in imagegen tool. The manga prompt records and the roster expansions are retained under [prompts](prompts/). They document prompts, references and output hashes where recorded. Initial color-generation prompts and the first Urahara manga prompt were not fully preserved in the available records; the repository does not invent provenance for those earlier assets. Local reference paths in these historical records have been normalized to `~/`; they describe the development setup, not installer destinations. Output files are now under `files/.config/fastfetch/portraits/` and `files/.config/fastfetch/manga/`.

The code's MIT license does not grant rights in Bleach characters, names, trademarks, or the character artwork. No ownership of third-party Bleach intellectual property or endorsement is claimed. Review these separate artwork terms and your intended use before redistribution. No blanket commercial-use license for the artwork is provided by this repository.

Nemu Kurotsuchi, Askin Nakk Le Vaar, Lille Barro and Yachiru Kusajishi were added on 2026-10-20 with matching color and manga portraits. [Exact prompts, references and output hashes](prompts/additions-20261020/PROMPTS.json) are preserved for all eight new assets.

## Login and boot artwork

The [manga login screen](../login/README.md) includes twelve black-and-white manga scene conversions of the full desktop wallpapers. [Exact prompt, source references, dimensions and hashes](../login/ARTWORK.json) are preserved. The built-in imagegen tool produced these scene edits; the TYBW expansion adds four backgrounds, corrects Ichigo and Yamamoto, and adds separate True Shikai Ichigo and Bankai Kenpachi terminal portraits. [Expansion prompts and hashes](prompts/tybw-expansion-20261020/PROMPTS.json) record the changes. The original Dangai portrait asset remains for migration compatibility. The paper layout, ink borders and lettering are drawn by QML; `login/preview.png` uses dummy login data. These unofficial fan-art scenes follow the same separate artwork terms above.

The [Ichigo boot splash](../boot/README.md) has its own [asset and prompt record](../boot/ARTWORK.json). Its character cutout is also excluded from the code MIT license. Aura, particle and loading-bar assets are generated from code-native geometry. Hollow-mask boot assets have been removed; the current splash always uses Ichigo.

## Rust application icon

The Hollow crest in `desktop/rust/assets/bleach-tray.svg` is original SVG geometry authored for this project, with a bone-white mask, ink-dark badge and recolorable crimson markings. It uses no downloaded logo, manga panel or generated bitmap. [Launcher and tray size preview](screenshots/rust-icon.png). The Bleach-inspired design is unofficial.
