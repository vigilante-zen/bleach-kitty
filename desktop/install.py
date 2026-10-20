#!/usr/bin/env python3
"""Install a Bankai desktop edition, with shared ownership and original-file backups."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = ('.local/bin/', '.local/share/bleach-desktop/', '.local/share/color-schemes/',
            '.local/share/icons/hicolor/scalable/apps/', '.local/share/applications/',
            'Pictures/Bleach-TYBW/Wallpapers/')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def confined(path, home):
    if not path.is_relative_to(home):
        raise ValueError('Path escapes installation home')
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError(f'Symlink destination is unsupported: {part}')
        if part == home:
            break
    if path.exists() and not path.is_file():
        raise ValueError(f'Expected a regular file: {path}')


def atomic(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def locked(state, home, dry):
    confined(state / 'install.lock', home)
    if dry:
        yield
    else:
        state.mkdir(parents=True, exist_ok=True)
        with (state / 'install.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield


def payload(edition, home, binary=None, dry=False):
    result = {}
    def add(source, target, mode=0o644):
        if source.is_symlink() or not source.is_file():
            raise ValueError(f'Missing or linked package file: {source}')
        result[target] = (source.read_bytes(), mode)
    for folder, target in [('wallpapers', 'Pictures/Bleach-TYBW/Wallpapers'),
                           ('color-schemes', '.local/share/color-schemes')]:
        sources = sorted((ROOT / 'desktop/shared' / folder).glob('*'))
        if len(sources) != 8:
            raise ValueError(f'Expected eight shared {folder} files')
        for source in sources:
            add(source, target + '/' + source.name)
    add(ROOT / 'desktop/README.md', '.local/share/bleach-desktop/README.md')
    add(ROOT / 'login/install.py', '.local/share/bleach-desktop/install-login.py')
    add(ROOT / 'login/README.md', '.local/share/bleach-desktop/login-README.md')
    for item in sorted((ROOT / 'login/theme').rglob('*')):
        if item.is_file():
            add(item, '.local/share/bleach-desktop/login-theme/' + str(item.relative_to(ROOT / 'login/theme')))
    source = ROOT / 'desktop' / edition
    guide_target = '.local/share/bleach-desktop/' + edition
    for name in ['README.md', 'INSTALL.md']:
        add(source / name, guide_target + '/' + name)
    if edition == 'python':
        for name in ['control_center.py', 'snapshot_manager.py']:
            add(source / name, '.local/share/bleach-desktop/' + name)
        for item in sorted((source / 'icons').glob('*.svg')):
            add(item, '.local/share/bleach-desktop/icons/' + item.name)
        for name in ['bankai', 'bankai-desktop', 'bankai-desktop-backup', 'bankai-desktop-restore']:
            add(source / 'bin' / name, '.local/bin/' + name, 0o755)
        command, icon = 'bankai', 'bleach-bankai'
        icon_source = source / 'icons/bleach-tray.svg'
    else:
        packaged = source / 'bin/bankai-rust'
        if binary is not None:
            add(binary, '.local/bin/bankai-rust', 0o755)
        elif packaged.is_file():
            add(packaged, '.local/bin/bankai-rust', 0o755)
        elif dry:
            print('Would build Rust using cargo build --release --locked')
            result['.local/bin/bankai-rust'] = (b'pending Rust build', 0o755)
        else:
            subprocess.run(['cargo', 'build', '--release', '--locked'], cwd=source, check=True)
            add(source / 'target/release/bankai-rust', '.local/bin/bankai-rust', 0o755)
        command, icon = 'bankai-rust', 'bleach-bankai-rust'
        icon_source = source / 'assets/bleach-tray.svg'
    add(icon_source, '.local/share/icons/hicolor/scalable/apps/' + icon + '.svg')
    executable = str(home / '.local/bin' / command)
    escaped = executable.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    exec_line = f'"{escaped}"'
    if edition == 'python':
        interpreter = sys.executable.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
        exec_line = f'"{interpreter}" ' + exec_line
    entry = f'[Desktop Entry]\nType=Application\nName=Bankai {edition.title()}\nExec={exec_line}\nIcon={icon}\nTerminal=false\nCategories=Settings;DesktopSettings;\nStartupNotify=false\n'
    result['.local/share/applications/' + icon + '.desktop'] = (entry.encode(), 0o644)
    return result


def load_receipt(path, home):
    confined(path, home)
    info = json.loads(path.read_text()) if path.exists() else {'version': 1, 'files': {}}
    if info.get('version') != 1 or not isinstance(info.get('files'), dict):
        raise ValueError('Invalid desktop installation receipt')
    for relative, entry in info['files'].items():
        if not relative.startswith(PREFIXES) or '..' in Path(relative).parts or str(Path(relative)) != relative:
            raise ValueError('Invalid managed file path')
        if not isinstance(entry.get('owners'), list) or not entry['owners'] or not set(entry['owners']) <= {'python', 'rust'}:
            raise ValueError('Invalid edition ownership')
        if not isinstance(entry.get('sha256'), str) or len(entry['sha256']) != 64 or not isinstance(entry.get('original'), bool):
            raise ValueError('Invalid managed file record')
        confined(home / relative, home)
    return info


def change(edition, action, home, state, files, dry):
    receipt = state / 'receipt.json'
    info = load_receipt(receipt, home)
    updated = deepcopy(info)
    changes = {}
    if action == 'install':
        for relative, (data, mode) in files.items():
            target = home / relative
            confined(target, home)
            entry = updated['files'].get(relative)
            if entry:
                if target.exists() and digest(target.read_bytes()) != entry['sha256']:
                    raise ValueError(f'File was edited locally; keep or back it up before updating: {target}')
                entry['owners'] = sorted(set(entry['owners']) | {edition})
                entry['sha256'] = digest(data)
            else:
                updated['files'][relative] = {'owners': [edition], 'sha256': digest(data), 'original': target.exists()}
            changes[relative] = (data, mode)
    else:
        found = False
        for relative, entry in list(updated['files'].items()):
            if edition not in entry['owners']:
                continue
            found = True
            if len(entry['owners']) > 1:
                entry['owners'].remove(edition)
                continue
            target = home / relative
            if target.exists() and digest(target.read_bytes()) != entry['sha256']:
                print('Kept modified file (still tracked):', target)
                continue
            if entry['original']:
                saved = state / 'originals' / relative
                confined(saved, home)
                if not saved.is_file():
                    raise ValueError(f'Original backup is missing: {relative}')
                changes[relative] = (saved.read_bytes(), saved.stat().st_mode & 0o777)
            else:
                changes[relative] = None
            del updated['files'][relative]
        if not found:
            raise ValueError(f'{edition.title()} has no desktop installation receipt')
    for relative, entry in updated['files'].items():
        if action == 'install' and relative in files and relative not in info['files'] and entry['original']:
            confined(state / 'originals' / relative, home)
    print(f'{"Would " if dry else ""}{action.title()} {edition}: {len(changes)} files in {home}')
    if dry:
        return
    before = {}
    for relative in changes:
        target = home / relative
        before[relative] = (target.read_bytes(), target.stat().st_mode & 0o777) if target.exists() else None
        if action == 'install' and relative not in info['files'] and before[relative] is not None:
            atomic(state / 'originals' / relative, *before[relative])
    try:
        for relative, content in changes.items():
            target = home / relative
            if content is None:
                target.unlink(missing_ok=True)
            else:
                atomic(target, *content)
        atomic(receipt, (json.dumps(updated, indent=2) + '\n').encode())
    except OSError:
        for relative, content in before.items():
            if content is None:
                (home / relative).unlink(missing_ok=True)
            else:
                atomic(home / relative, *content)
        raise
    print('Original-file backups and receipt:', state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('edition', choices=['python', 'rust'])
    parser.add_argument('action', nargs='?', default='install', choices=['install', 'uninstall'])
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-theme', action='store_true', help='install only desktop files; theme must already be available')
    parser.add_argument('--binary', type=Path, help='use an already built Rust executable')
    args = parser.parse_args()
    home = args.home.expanduser().absolute()
    if home == Path('/') or home.is_symlink():
        raise ValueError('Use a real, non-root home directory')
    state = home / '.local/state/bankai-desktop-install'
    with locked(state, home, args.dry_run):
        files = payload(args.edition, home, args.binary, args.dry_run) if args.action == 'install' else {}
        # Validate the whole desktop transaction before starting the separate theme installer.
        if args.action == 'install':
            change(args.edition, args.action, home, state, files, True)
            if not args.skip_theme:
                theme_receipt = home / '.local/state/bleach-kitty-install/receipt.json'
                confined(theme_receipt, home)
                if not theme_receipt.exists():
                    command = [sys.executable, str(ROOT / 'install.py'), '--home', str(home)]
                    subprocess.run(command + (['--dry-run'] if args.dry_run else []), check=True)
            if args.dry_run:
                return
        change(args.edition, args.action, home, state, files, args.dry_run)
    if args.action == 'install' and not args.dry_run:
        print('Optional login theme: sudo python3 ~/.local/share/bleach-desktop/install-login.py install')
        print(f'Open Bankai {args.edition.title()} from your app menu. Login startup stays unchanged.')
    if args.action == 'uninstall':
        print('Theme files, runtime preferences, snapshots and login-startup settings are retained. Disable login startup in the app before uninstalling.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f'bankai-install: {error}', file=sys.stderr)
        sys.exit(1)
