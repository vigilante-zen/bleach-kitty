#!/usr/bin/env python3
"""Install or uninstall the Bleach Kitty theme, with per-file backups."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import sys
import tempfile

REPO = Path(__file__).resolve().parent
BEGIN = '# BEGIN BLEACH KITTY (managed by bleach-kitty)'
END = '# END BLEACH KITTY'
DEFAULTS = {'.config/fastfetch/' + name for name in
            ['portrait-choice', 'portrait-art-mode', 'greeting-mode', 'shuffle-mode']}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_path(path, home):
    for candidate in [path, *path.parents]:
        if candidate == home:
            break
        if candidate.is_symlink():
            raise ValueError(f'Symlink destination: {candidate}; install manually instead.')
    if path.exists() and not path.is_file():
        raise ValueError(f'Destination is not a file: {path}')


def payload(home, updating=False):
    manifest = json.loads((REPO / 'MANIFEST.json').read_text())
    result = {}
    for relative, expected in manifest.items():
        rel = Path(relative)
        if rel.is_absolute() or '..' in rel.parts or not relative.startswith('.'):
            raise ValueError('Invalid payload manifest path')
        source = REPO / 'files' / rel
        data = source.read_bytes()
        if digest(data) != expected:
            raise ValueError(f'Payload checksum mismatch: {relative}')
        if source.suffix != '.png':
            data = data.replace(b'__BANKAI_HOME__', str(home).encode())
        result[relative] = (data, source.stat().st_mode & 0o777)
    kitty = '.config/kitty/kitty.conf'
    check_path(home / kitty, home)
    previous = (home / kitty).read_text() if (home / kitty).exists() else ''
    if updating:
        return result
    if BEGIN in previous or END in previous:
        raise ValueError('A managed Kitty block already exists. Uninstall first.')
    existing = set()
    for line in previous.splitlines():
        try:
            parts = shlex.split(line, comments=True)
        except ValueError:
            continue
        if len(parts) == 2 and parts[0] == 'include':
            path = Path(os.path.expandvars(parts[1])).expanduser()
            existing.add((home / '.config/kitty' / path).resolve())
    includes = ['include themes/' + name + '.conf' for name in
                ['bleach-tybw', 'bleach-effects', 'bleach-v5', 'bleach-shortcuts']
                if (home / '.config/kitty/themes' / (name + '.conf')).resolve() not in existing]
    block = '\n' + BEGIN + '\n' + '\n'.join(includes) + '\n' + END + '\n'
    result[kitty] = ((previous + block).encode(), 0o644)
    return result



def update(home, state, receipt, dry):
    check_path(receipt, home)
    info = json.loads(receipt.read_text())
    backup = Path(info['backup'])
    if not backup.is_relative_to(state): raise ValueError('Invalid backup directory')
    entries = {row['path']: row.copy() for row in info['files']}
    files = payload(home, updating=True)
    changes = {}
    for relative, (data, mode) in files.items():
        target = home / relative; check_path(target, home)
        if relative in DEFAULTS and target.exists(): continue
        entry = entries.get(relative)
        if entry and target.exists() and digest(target.read_bytes()) != entry['sha256']:
            print('Kept modified file:', target); continue
        if target.exists() and target.read_bytes() == data: continue
        if not entry:
            existed = target.exists()
            if existed:
                saved = backup / relative; check_path(saved, home)
                if not dry:
                    saved.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(target, saved)
            entry = {'path': relative, 'existed': existed}; entries[relative] = entry
        entry['sha256'] = digest(data); changes[relative] = (data, mode)
    print(f'{"Would update" if dry else "Update"} {len(changes)} terminal files; preferences and local edits retained')
    if dry: return
    before = {relative: ((home / relative).read_bytes(), (home / relative).stat().st_mode & 0o777) if (home / relative).exists() else None for relative in changes}
    def atomic(path, data, mode=0o644):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream: stream.write(data)
            os.chmod(temp, mode); os.replace(temp, path)
        finally: Path(temp).unlink(missing_ok=True)
    try:
        for relative, content in changes.items(): atomic(home / relative, *content)
        atomic(receipt, (json.dumps({'backup': str(backup), 'files': list(entries.values())}, indent=2) + '\n').encode())
    except OSError:
        for relative, content in before.items():
            if content is None: (home / relative).unlink(missing_ok=True)
            else: atomic(home / relative, *content)
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='install', choices=['install', 'update', 'uninstall'])
    parser.add_argument('--home', type=Path, default=Path.home(), help='target home (also useful for isolated testing)')
    parser.add_argument('--dry-run', action='store_true', help='validate and show file count without writing')
    args = parser.parse_args()
    home = args.home.expanduser().absolute()
    state = home / '.local/state/bleach-kitty-install'
    receipt = state / 'receipt.json'
    if args.action == 'update':
        if not receipt.is_file(): raise ValueError('No terminal installation receipt; install first.')
        update(home, state, receipt, args.dry_run)
        return
    if args.action == 'install':
        if receipt.exists():
            raise ValueError('Already installed. Uninstall this package before reinstalling; your backup is retained.')
        files = payload(home)
        files = {r: v for r, v in files.items() if r not in DEFAULTS or not (home / r).exists()}
        for relative in files:
            check_path(home / relative, home)
        check_path(receipt, home)
        print(f'Install {len(files)} files into {home}')
        if args.dry_run:
            return
        backup = state / ('backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir(parents=True)
        entries = []
        # Back up every existing destination before writing any theme files.
        for relative, (data, mode) in files.items():
            target = home / relative
            existed = target.exists()
            if existed:
                saved = backup / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
            entries.append({'path': relative, 'existed': existed, 'sha256': digest(data)})
        receipt.write_text(json.dumps({'backup': str(backup), 'files': entries}, indent=2) + '\n')
        try:
            for relative, (data, mode) in files.items():
                target = home / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                target.chmod(mode)
        except OSError:
            print('Install interrupted; run uninstall to restore the saved files.', file=sys.stderr)
            raise
        print(f'Backup: {backup}\nOpen a new Kitty window. Run bankai-doctor to check the setup.')
    else:
        if not receipt.is_file():
            raise ValueError('No installation receipt found for this home.')
        info = json.loads(receipt.read_text())
        backup = Path(info['backup'])
        entries = info['files']
        for entry in entries:
            relative = Path(entry['path'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Invalid receipt path')
            check_path(home / relative, home)
            if entry['existed'] and not (backup / relative).is_file():
                raise ValueError(f'Backup is missing: {relative}')
        print(f'Uninstall {len(entries)} managed files from {home}')
        if args.dry_run:
            return
        retained = []
        for entry in reversed(entries):
            target = home / entry['path']
            if target.exists() and digest(target.read_bytes()) != entry['sha256']:
                if entry['path'] == '.config/kitty/kitty.conf':
                    text = target.read_text()
                    if BEGIN in text and END in text:
                        start = text.index(BEGIN)
                        if start and text[start - 1] == '\n':
                            start -= 1
                        stop = text.index(END, start) + len(END)
                        if text[stop:stop + 1] == '\n':
                            stop += 1
                        target.write_text(text[:start] + text[stop:])
                        continue
                print('Kept modified file: ' + str(target))
                retained.append(entry)
                continue
            if entry['existed']:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup / entry['path'], target)
            else:
                target.unlink(missing_ok=True)
        if retained:
            info['files'] = retained
            receipt.write_text(json.dumps(info, indent=2) + '\n')
            print('Modified files retained in receipt; backups remain available for manual restoration.')
        else:
            receipt.unlink()
            print('Original files restored. Backup retained: ' + str(backup))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f'bleach-kitty: {error}', file=sys.stderr)
        sys.exit(1)
