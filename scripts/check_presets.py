#!/usr/bin/env python3
"""Validate that every shared Bankai preset has a complete, consistent asset set."""
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


def _png_size(path):
    try:
        with path.open('rb') as stream:
            header = stream.read(24)
    except OSError as exc:
        raise ValueError(f'Cannot read {path}: {exc}') from exc
    if len(header) != 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b'IHDR':
        raise ValueError(f'Not a valid PNG header: {path}')
    width, height = struct.unpack('>II', header[16:24])
    if not width or not height:
        raise ValueError(f'PNG has invalid dimensions: {path}')
    return width, height


def validate(root=ROOT):
    root = Path(root)
    catalog_path = root / 'desktop/shared/presets.json'
    try:
        catalog = json.loads(catalog_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f'Cannot load preset catalog {catalog_path}: {exc}']
    rows = catalog.get('presets') if isinstance(catalog, dict) else None
    if not isinstance(rows, list) or not rows:
        return ['Preset catalog must contain a non-empty presets array']

    errors = []
    required = {'id', 'title', 'subtitle', 'accent', 'image', 'portrait', 'manga'}
    ids, titles, images, manga_files = set(), set(), set(), set()
    wallpaper_dir = root / 'desktop/shared/wallpapers'
    scheme_dir = root / 'desktop/shared/color-schemes'
    scene_dir = root / 'login/theme/assets'
    for index, row in enumerate(rows):
        label = f'preset #{index + 1}'
        if not isinstance(row, dict):
            errors.append(f'{label} must be an object')
            continue
        missing = required - row.keys()
        if missing:
            errors.append(f'{label} is missing fields: {", ".join(sorted(missing))}')
            continue
        preset_id, title = row['id'], row['title']
        if not isinstance(preset_id, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', preset_id):
            errors.append(f'{label} has an invalid id: {preset_id!r}')
            continue
        label = f'preset {preset_id}'
        if preset_id in ids:
            errors.append(f'{label} has a duplicate id')
        ids.add(preset_id)
        if not isinstance(title, str) or not title.strip():
            errors.append(f'{label} has an empty title')
        elif title in titles:
            errors.append(f'{label} has a duplicate title: {title}')
        else:
            titles.add(title)
        if not isinstance(row['subtitle'], str) or not row['subtitle'].strip():
            errors.append(f'{label} has an empty subtitle')
        if not isinstance(row['accent'], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', row['accent']):
            errors.append(f'{label} has an invalid accent color: {row["accent"]!r}')
        if not isinstance(row['portrait'], str) or not row['portrait'].strip():
            errors.append(f'{label} has an empty portrait choice')
        for field in ('image', 'manga'):
            value = row[field]
            if not isinstance(value, str) or Path(value).name != value or not value.endswith('.png'):
                errors.append(f'{label} has an invalid {field} filename: {value!r}')
                continue
            if field == 'image':
                if value in images:
                    errors.append(f'{label} reuses desktop wallpaper {value}')
                images.add(value)
                path = wallpaper_dir / value
            else:
                if value in manga_files:
                    errors.append(f'{label} reuses manga wallpaper {value}')
                manga_files.add(value)
                path = scene_dir / f'scene-{preset_id}.png'
                if value != f'{preset_id}-manga.png':
                    errors.append(f'{label} manga filename must be {preset_id}-manga.png to match scene packaging')
            if not path.is_file():
                errors.append(f'{label} is missing {field} artwork: {path.relative_to(root)}')
            else:
                try:
                    _png_size(path)
                except ValueError as exc:
                    errors.append(str(exc))
        if isinstance(title, str) and title.strip():
            scheme = scheme_dir / f'Bleach{title}.colors'
            if not scheme.is_file():
                errors.append(f'{label} is missing color scheme: {scheme.relative_to(root)}')

    expected = {
        'desktop wallpapers': (wallpaper_dir, images, '*.png'),
        'color schemes': (scheme_dir, {f'Bleach{title}.colors' for title in titles}, '*.colors'),
        'login scenes': (scene_dir, {f'scene-{preset_id}.png' for preset_id in ids}, 'scene-*.png'),
    }
    for description, (directory, expected_names, pattern) in expected.items():
        actual = {path.name for path in directory.glob(pattern)} if directory.is_dir() else set()
        for name in sorted(expected_names - actual):
            errors.append(f'Missing {description} asset: {name}')
        for name in sorted(actual - expected_names):
            errors.append(f'Unexpected {description} asset: {name}')
    return errors


def main():
    errors = validate()
    if errors:
        print('FAIL: preset assets are inconsistent')
        for error in errors:
            print(f' - {error}')
        raise SystemExit(1)
    count = len(json.loads((ROOT / 'desktop/shared/presets.json').read_text())['presets'])
    print(f'PASS: {count} presets have matching desktop wallpapers, manga scenes, and color schemes.')


if __name__ == '__main__':
    main()
