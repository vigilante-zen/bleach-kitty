#!/usr/bin/env python3
"""Install/restore Bankai's optional system Plymouth theme and rebuild boot images."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent / 'theme'
NAME = 'bankai-random'


def atomic(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.chmod(temporary, mode); os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def safe(path, root):
    if not path.is_relative_to(root):
        raise ValueError('Path escapes selected system root')
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError(f'Symlink destination is unsupported: {part}')
        if part == root:
            break


def theme_name(text):
    section = ''
    for line in text.splitlines():
        if line.strip().startswith('['): section = line.strip()
        elif section == '[Daemon]' and re.match(r'^\s*Theme\s*=', line):
            return line.split('=', 1)[1].strip()
    return 'details'


def set_theme(text, theme):
    lines = text.splitlines(); start = next((i for i, line in enumerate(lines) if line.strip() == '[Daemon]'), None)
    if start is None:
        return text.rstrip() + '\n[Daemon]\nTheme=' + theme + '\n'
    end = next((i for i in range(start+1, len(lines)) if lines[i].strip().startswith('[')), len(lines))
    matches = [i for i in range(start+1, end) if re.match(r'^\s*Theme\s*=', lines[i])]
    if len(matches) > 1: raise ValueError('Multiple Theme entries; resolve before installation')
    if matches: lines[matches[0]] = 'Theme=' + theme
    else: lines.insert(end, 'Theme=' + theme)
    return '\n'.join(lines) + '\n'


def locations(root):
    return root/'usr/share/plymouth/themes'/NAME, root/'etc/plymouth/plymouthd.conf', root/'var/lib/bankai-plymouth'


def rebuild_command(root):
    if (root/'etc/default/limine').is_file():
        return ['/usr/bin/limine-mkinitcpio']
    return ['/usr/bin/mkinitcpio', '-P']


def prepare(root, action, mode):
    destination, config, state = locations(root)
    for path in [destination, config, state/'receipt.json', state/'original.conf', state/'install.lock']:
        safe(path, root)
    if destination.exists():
        for path in destination.rglob('*'): safe(path, root)
    receipt = json.loads((state/'receipt.json').read_text()) if (state/'receipt.json').exists() else None
    if receipt and (receipt.get('version') != 1 or not isinstance(receipt.get('files'), dict)):
        raise ValueError('Invalid boot-theme receipt')
    if receipt and not (state/'original.conf').is_file():
        raise ValueError('Original Plymouth configuration backup is missing')
    if destination.exists():
        if not receipt: raise ValueError('Theme directory already exists without a receipt; refusing to overwrite')
        actual = {str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()}
        if actual != set(receipt['files']): raise ValueError('Installed theme file list changed; preserve local edits first')
        for relative, expected in receipt['files'].items():
            if '..' in Path(relative).parts or Path(relative).is_absolute(): raise ValueError('Invalid theme receipt path')
            if hashlib.sha256((destination/relative).read_bytes()).hexdigest() != expected:
                raise ValueError(f'Installed theme edited: {relative}')
    if action == 'remove' and not receipt: raise ValueError('No Bankai boot-theme installation receipt')
    text = config.read_text() if config.exists() else ''
    if action == 'install':
        hooks = root/'etc/mkinitcpio.conf'
        if not hooks.is_file() or not re.search(r'^HOOKS=\([^)]*\bplymouth\b', hooks.read_text(), re.M|re.S):
            raise ValueError('Enable the plymouth mkinitcpio hook before installing this theme')
        files = {}
        for source in SOURCE.rglob('*'):
            if not source.is_file(): continue
            if source.is_symlink(): raise ValueError('Unexpected theme package symlink')
            relative = str(source.relative_to(SOURCE));data = source.read_bytes()
            files[relative] = data
        if not {'bankai.script', NAME+'.plymouth', 'assets/silhouette.png'} <= set(files):
            raise ValueError('Boot-theme package is incomplete')
        return files, set_theme(text, NAME).encode(), receipt
    # If other config settings changed since installation, preserve them.
    original = state/'original.conf'
    if not original.is_file(): raise ValueError('Original Plymouth configuration backup is missing')
    if hashlib.sha256(text.encode()).hexdigest() == receipt['config_sha256']:
        restored = original.read_bytes()
    elif theme_name(text) == NAME:
        restored = set_theme(text, receipt['previous_theme']).encode()
    else: restored = text.encode()
    return {}, restored, receipt


def perform(root, action, mode, rebuild=False):
    destination, config, state = locations(root)
    files, new_config, old_receipt = prepare(root, action, mode)
    old_config = config.read_bytes() if config.exists() else None
    old_mode = config.stat().st_mode & 0o777 if config.exists() else 0o644
    state.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='transaction-', dir=state) as temporary:
        snapshot = Path(temporary)/'theme'
        if destination.exists(): shutil.copytree(destination, snapshot)
        old_state = (state/'receipt.json').read_bytes() if old_receipt else None
        try:
            if action == 'install':
                if not old_receipt:
                    atomic(state/'original.conf', old_config or b'', old_mode)
                if destination.exists(): shutil.rmtree(destination)
                for relative, data in files.items(): atomic(destination/relative, data)
                record = old_receipt or {'version':1, 'previous_theme':theme_name((old_config or b'').decode()), 'config_existed':old_config is not None, 'config_mode':old_mode}
                record.update({'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}, 'config_sha256':hashlib.sha256(new_config).hexdigest(), 'mode':mode})
                atomic(config,new_config,old_mode)
                atomic(state/'receipt.json',(json.dumps(record,indent=2)+'\n').encode(),0o600)
            else:
                shutil.rmtree(destination,ignore_errors=False) if destination.exists() else None
                if not old_receipt['config_existed'] and not new_config:
                    config.unlink(missing_ok=True)
                else: atomic(config,new_config,old_receipt['config_mode'])
                (state/'receipt.json').unlink()
            if rebuild: subprocess.run(rebuild_command(root),check=True)
        except (OSError, subprocess.CalledProcessError):
            if destination.exists(): shutil.rmtree(destination)
            if snapshot.exists(): shutil.copytree(snapshot,destination)
            if old_config is None:config.unlink(missing_ok=True)
            else:atomic(config,old_config,old_mode)
            if old_state is None:(state/'receipt.json').unlink(missing_ok=True)
            else:atomic(state/'receipt.json',old_state,0o600)
            if rebuild:
                print('Restored the previous theme/configuration; attempting to rebuild the previous boot image.',file=sys.stderr)
                try:subprocess.run(rebuild_command(root),check=True)
                except (OSError,subprocess.CalledProcessError):
                    print('Recovery rebuild failed. Resolve the reported initramfs error before rebooting.',file=sys.stderr)
            raise
    print('Installed Bankai Ichigo boot theme.' if action=='install' else 'Restored the previous Plymouth theme.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',nargs='?',default='install',choices=['install','remove'])
    parser.add_argument('--mode',choices=['silhouette'],default='silhouette')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--root',type=Path,default=Path('/'),help='alternate staging system root; never rebuilds the host boot images')
    args=parser.parse_args();root=args.root.absolute()
    if root.is_symlink():raise ValueError('System root cannot be a symlink')
    if args.dry_run:
        files,_,_=prepare(root,args.action,args.mode)
        print(f'Would {args.action} {NAME} ({args.mode}); {len(files)} theme assets/config files.')
        print('Boot image command:', ' '.join(rebuild_command(root)) if root==Path('/') else 'none (staging root)');return
    if root==Path('/') and os.geteuid()!=0:raise ValueError('System activation requires sudo. Run a dry preview with --dry-run first.')
    _,_,state=locations(root);safe(state/'install.lock',root);state.mkdir(parents=True,exist_ok=True)
    with (state/'install.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        perform(root,args.action,args.mode,rebuild=root==Path('/'))


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError,subprocess.CalledProcessError) as error:
        print('bankai-boot:',error,file=sys.stderr);sys.exit(1)
