#!/usr/bin/env python3
"""Rebuild the GitHub and local portrait galleries from the installed roster payload."""
import html
import sys
import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader('gallery_roster', str(ROOT / 'files/.local/bin/bankai-roster'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    roster = importlib.util.module_from_spec(spec); loader.exec_module(roster)
    base = ROOT / 'files/.config/fastfetch'
    ids = sorted(p.stem for p in (base / 'portraits').glob('*.png'))
    if set(ids) != {p.stem for p in (base / 'manga').glob('*.png')}:
        raise ValueError('Color and manga portraits must have matching filenames')
    rows = sorted([(name, roster.DISPLAY_NAMES.get(name, name.replace('-', ' ').title())) for name in ids], key=lambda row: row[1].casefold())
    latest = ['ichigo-tybw', 'kenpachi-bankai', 'nemu', 'askin', 'lille', 'yachiru']
    latest = [name for name in latest if name in ids]
    rows.sort(key=lambda row: (0, latest.index(row[0])) if row[0] in latest else (1, row[1].casefold()))
    markdown = ['# Color and manga portrait gallery', '', '[Back to Bankai](../README.md) · [Artwork provenance](ARTWORK.md)', '',
                f'{len(ids)} portraits, with color and manga editions side by side. Click a portrait to view the original image. Manga uses ink, screentones and restrained character accents.', '',
                'Newest first: TYBW Ichigo and Bankai Kenpachi, followed by Nemu, Askin, Lille and Yachiru — added October 20, 2026.', '',
                '| Character | Color | Manga |', '| --- | --- | --- |']
    articles = []
    for name, label in rows:
        cells = []; images = []
        for folder, edition in [('portraits', 'Color'), ('manga', 'Manga')]:
            target = f'../files/.config/fastfetch/{folder}/{name}.png'
            alt = html.escape(label + ' — ' + edition, quote=True)
            cells.append(f'[<img src="{target}" alt="{alt}" width="220">]({target})')
            images.append(f'<a href="../{folder}/{name}.png"><img loading="lazy" src="../{folder}/{name}.png" alt="{alt}"><span>{edition}</span></a>')
        markdown.append('| ' + label.replace('|', '\\|') + ' | ' + ' | '.join(cells) + ' |')
        articles.append('<article><h2>' + html.escape(label) + '</h2><div class="pair">' + ''.join(images) + '</div></article>')
    (ROOT / 'docs/GALLERY.md').write_text('\n'.join(markdown) + '\n')
    gallery = base / 'previews/manga-roster.html'
    prefix = gallery.read_text().split('<body>', 1)[0]
    gallery.write_text(prefix + f'<body><header><h1>Bleach · Color and Manga</h1><p>{len(ids)} portraits, two editions. Newest first: TYBW Ichigo and Bankai Kenpachi, followed by Nemu, Askin, Lille and Yachiru. Click an image to inspect it at full size.</p></header><main>' + ''.join(articles) + '</main></body></html>')
    print(f'Rebuilt both galleries: {len(ids)} portraits / {len(ids)*2} images.')


if __name__ == '__main__':
    main()
