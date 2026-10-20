#!/usr/bin/env python3
"""Install, update or restore Bankai's optional SDDM login theme."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

BASE = Path(__file__).resolve().parent
THEME = BASE / 'login-theme' if (BASE / 'login-theme').is_dir() else BASE / 'theme'
THEME_FILES = ('Main.qml', 'metadata.desktop', 'theme.conf', 'assets/ichigo.png')
CONFIG = b'[Theme]\nCurrent=bankai-manga\n'

def sha(data): return hashlib.sha256(data).hexdigest()

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream: stream.write(data)
        os.chmod(temp, 0o644)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)

def apply(action, root, dry=False):
    root = root.resolve()
    if root == Path('/') and not dry and os.geteuid() != 0:
        raise ValueError('Administrator access required; run this command with sudo.')
    state = root / 'var/lib/bankai-login/receipt.json'
    config = root / 'etc/sddm.conf.d/zz-bankai-manga.conf'
    target = root / 'usr/share/sddm/themes/bankai-manga'
    def check(path):
        for part in (path, *path.parents):
            if part.is_symlink(): raise ValueError(f'Symlink destination refused: {part}')
            if part == root: break
    for path in (state, config, target): check(path)
    expected = None
    if state.exists():
        expected = json.loads(state.read_text())
        if not isinstance(expected, dict) or any(not isinstance(k, str) or '..' in Path(k).parts or Path(k).is_absolute() for k in expected):
            raise ValueError('Invalid login receipt')
        current = {str(p.relative_to(target)): sha(p.read_bytes()) for p in target.rglob('*') if p.is_file()}
        if any(p.is_symlink() for p in target.rglob('*')) or current != expected:
            raise ValueError('Login theme was edited; preserve or resolve edits before updating/restoring.')
        if not config.is_file() or config.read_bytes() != CONFIG:
            raise ValueError('Login selection was edited; left untouched.')
    elif config.exists() or target.exists():
        # Adopt only a byte-for-byte match of the original standalone installer.
        source = {name: sha((THEME / name).read_bytes()) for name in THEME_FILES}
        current = {str(p.relative_to(target)): sha(p.read_bytes()) for p in target.rglob('*') if p.is_file()}
        if (not source or current != source or not config.is_file() or config.read_bytes() != CONFIG
                or any(p.is_symlink() for p in target.rglob('*'))):
            raise ValueError('Unmanaged Bankai login files differ from this theme; preserve or remove them before installing.')
        expected = current
        print('Recognized exact standalone Bankai theme; migrating to managed installation.')
    if action == 'restore':
        if expected is None:
            print('No managed login theme installed.'); return
        print(('Would restore' if dry else 'Restoring') + ' previous SDDM selection')
        if not dry:
            config.unlink(); shutil.rmtree(target); state.unlink(missing_ok=True)
        return
    if root == Path('/') and not (root / 'usr/share/sddm').is_dir():
        raise ValueError('SDDM is not installed.')
    files = {}
    for name in THEME_FILES:
        path = THEME / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError('Linked source theme is unsupported')
        files[name] = path.read_bytes()
    if not {'Main.qml', 'metadata.desktop', 'theme.conf', 'assets/ichigo.png'} <= files.keys():
        raise ValueError('Incomplete login theme package')
    for name in files: check(target / name)
    print(('Would install/update' if dry else 'Installing/updating') + ' Bankai Manga login theme')
    if dry: return
    # Save the entire prior transaction so failed writes can be rolled back.
    paths = {target / name for name in files} | {target / name for name in (expected or {})} | {config, state}
    before = {path: path.read_bytes() if path.is_file() else None for path in paths}
    try:
        for name, data in files.items(): atomic(target / name, data)
        for name in (expected or {}).keys() - files.keys(): (target / name).unlink()
        atomic(state, (json.dumps({k: sha(v) for k, v in files.items()}, indent=2) + '\n').encode())
        atomic(config, CONFIG)
    except OSError:
        for path, data in before.items():
            if data is None: path.unlink(missing_ok=True)
            else: atomic(path, data)
        raise
    print('Ready for next login. The current desktop was not restarted.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='install', choices=['install', 'restore'])
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--root', type=Path, default=Path('/'), help='system root for staging/testing')
    args = parser.parse_args()
    try: apply(args.action, args.root, args.dry_run)
    except (OSError, ValueError) as error: parser.exit(1, f'bankai-login: {error}\n')

if __name__ == '__main__': main()
