#!/usr/bin/env python3
"""Install, update or restore Bankai's optional character-following SDDM theme."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile

BASE = Path(__file__).resolve().parent
THEME = BASE / 'login-theme' if (BASE / 'login-theme').is_dir() else BASE / 'theme'
PREFIX = 'usr/share/sddm/themes/bankai-manga'
CONFIG_PATH = 'etc/sddm.conf.d/zz-bankai-manga.conf'
CONFIG = b'[Theme]\nCurrent=bankai-manga\n'
SERVICE = 'etc/systemd/system/bankai-login-sync.service'
WATCH = 'etc/systemd/system/bankai-login-sync.path'
FOLLOW = 'var/lib/bankai-login/follow.json'
DYNAMIC = PREFIX + '/theme.conf.user'
PRESETS = ('ichigo', 'rukia', 'quincy', 'tybw', 'urahara', 'byakuya', 'yamamoto', 'ulquiorra')
THEME_FILES = ('Main.qml', 'metadata.desktop', 'theme.conf', 'assets/ichigo.png') + tuple(f'assets/scene-{key}.png' for key in PRESETS)

def sha(data): return hashlib.sha256(data).hexdigest()

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream: stream.write(data)
        os.chmod(name, 0o644)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)

def systemctl(*args):
    subprocess.run(['/usr/bin/systemctl', *args], check=True)

def apply(action, root, dry=False, home=None, static=False):
    root = Path(root).resolve()
    live = root == Path('/')
    if live and not dry and os.geteuid() != 0:
        raise ValueError('Administrator access required; run this command with sudo.')
    state = root / 'var/lib/bankai-login/receipt.json'
    target = root / PREFIX
    def check(path):
        for part in (path, *path.parents):
            if part.is_symlink(): raise ValueError(f'Symlink destination refused: {part}')
            if part == root: break
    for name in (CONFIG_PATH, SERVICE, WATCH, FOLLOW, DYNAMIC, str(state.relative_to(root))):
        check(root / name)
    def current_theme():
        result = {}
        for path in target.rglob('*'):
            check(path)
            if path.is_file() and path != root / DYNAMIC:
                result[str(path.relative_to(target))] = sha(path.read_bytes())
        return result
    previous = {}
    previous_home = None
    if state.exists():
        receipt = json.loads(state.read_text())
        if receipt.get('version') == 2:
            previous = receipt['files']; previous_home = receipt.get('home')
        else:
            previous = {PREFIX + '/' + k: v for k, v in receipt.items()}
            previous[CONFIG_PATH] = sha(CONFIG)
        allowed = {CONFIG_PATH, SERVICE, WATCH, FOLLOW}
        for name, digest in previous.items():
            if (not isinstance(name, str) or '..' in Path(name).parts or Path(name).is_absolute()
                    or (not name.startswith(PREFIX + '/') and name not in allowed)):
                raise ValueError('Invalid login receipt')
            path = root / name; check(path)
            if not path.is_file() or sha(path.read_bytes()) != digest:
                raise ValueError(f'Managed login file was edited or removed: {path}')
        expected_theme = {k[len(PREFIX)+1:]: v for k, v in previous.items() if k.startswith(PREFIX + '/')}
        if current_theme() != expected_theme:
            raise ValueError('Untracked or edited login theme files; left untouched.')
    elif target.exists() or (root / CONFIG_PATH).exists():
        legacy = json.loads((BASE / 'legacy-theme.json').read_text())
        current = current_theme()
        source = {name: sha((THEME / name).read_bytes()) for name in THEME_FILES}
        # An exact legacy standalone installation or exact current static copy can be adopted.
        if current not in (legacy, source) or (root / CONFIG_PATH).read_bytes() != CONFIG:
            raise ValueError('Unmanaged Bankai login files differ from a known theme; left untouched.')
        previous = {PREFIX + '/' + k: v for k, v in current.items()}
        previous[CONFIG_PATH] = sha(CONFIG)
        print('Recognized standalone Bankai theme; migrating to managed installation.')
    for name in (SERVICE, WATCH, FOLLOW):
        if (root / name).exists() and name not in previous:
            raise ValueError(f'Unmanaged follow setup exists: {root / name}')
    dynamic = root / DYNAMIC
    if dynamic.exists() and dynamic.read_bytes() not in [f'[General]\nCharacter={key}\n'.encode() for key in PRESETS]:
        raise ValueError('Login character configuration was edited; left untouched.')
    if dynamic.exists() and not previous:
        raise ValueError('Unmanaged login character configuration exists')
    home = None if static else str(home or previous_home or '') or None
    if home and (not Path(home).is_absolute() or any(c in home for c in '\n\r\0')):
        raise ValueError('Use an absolute account home directory')
    if action == 'restore':
        if not previous:
            print('No managed login theme installed.'); return
        print(('Would restore' if dry else 'Restoring') + ' previous SDDM selection and removing follow setup')
        if dry: return
        if live and WATCH in previous: systemctl('disable', '--now', 'bankai-login-sync.path', 'bankai-login-sync.service')
        if live and SERVICE in previous: systemctl('stop', 'bankai-login-sync.service')
        for name in previous: (root / name).unlink()
        dynamic.unlink(missing_ok=True)
        shutil.rmtree(target)
        state.unlink(missing_ok=True)
        if live and SERVICE in previous: systemctl('daemon-reload')
        return
    if live and not (root / 'usr/share/sddm').is_dir():
        raise ValueError('SDDM is not installed.')
    files = {PREFIX + '/' + name: (THEME / name).read_bytes() for name in THEME_FILES}
    for name in THEME_FILES:
        if (THEME / name).is_symlink(): raise ValueError('Linked source theme is unsupported')
    files[CONFIG_PATH] = CONFIG
    if home:
        files[PREFIX + '/sync.py'] = (BASE / 'sync.py').read_bytes()
        files[FOLLOW] = (json.dumps({'home': home}) + '\n').encode()
        files[SERVICE] = b'''[Unit]
Description=Match Bankai login scene to desktop character
Before=display-manager.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/share/sddm/themes/bankai-manga/sync.py
ProtectSystem=strict
ReadWritePaths=/usr/share/sddm/themes/bankai-manga
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
'''
        marker = str(Path(home) / '.local/share/bleach-desktop/current').replace('%', '%%')
        files[WATCH] = ('[Unit]\nDescription=Watch Bankai desktop character\n\n[Path]\nPathChanged=' + json.dumps(marker) + '\n\n[Install]\nWantedBy=multi-user.target\n').encode()
    for name in files: check(root / name)
    print(('Would install/update' if dry else 'Installing/updating') + ' Bankai Manga' + (f', following {home}' if home else ', fixed Ichigo scene'))
    if dry: return
    # Stop the existing reader before replacing its code or configuration.
    if live and WATCH in previous: systemctl('stop', 'bankai-login-sync.path')
    if live and SERVICE in previous: systemctl('stop', 'bankai-login-sync.service')
    if live and WATCH in previous and not home:
        systemctl('disable', 'bankai-login-sync.path', 'bankai-login-sync.service')
    target_existed = target.exists()
    paths = {root / name for name in files.keys() | previous.keys()} | {state, dynamic}
    before = {path: path.read_bytes() if path.is_file() else None for path in paths}
    try:
        for name, data in files.items(): atomic(root / name, data)
        for name in previous.keys() - files.keys(): (root / name).unlink()
        atomic(state, (json.dumps({'version': 2, 'files': {k: sha(v) for k, v in files.items()}, 'home': home}, indent=2) + '\n').encode())
        if home:
            spec = importlib.util.spec_from_file_location('bankai_login_sync', BASE / 'sync.py')
            sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)
            if not dynamic.exists(): atomic(dynamic, b'[General]\nCharacter=ichigo\n')
            sync.sync(root, home)
        else: dynamic.unlink(missing_ok=True)
        if live:
            systemctl('daemon-reload')
            if home:
                systemctl('enable', '--now', 'bankai-login-sync.path')
                systemctl('enable', 'bankai-login-sync.service')
                systemctl('start', 'bankai-login-sync.service')

    except (OSError, subprocess.CalledProcessError):
        for path, data in before.items():
            if data is None: path.unlink(missing_ok=True)
            else: atomic(path, data)
        if not target_existed and target.exists(): shutil.rmtree(target)
        if live:
            systemctl('daemon-reload')
            if WATCH in previous: systemctl('enable', '--now', 'bankai-login-sync.path', 'bankai-login-sync.service')
        raise
    print('Ready for next login. No display-manager restart or logout was performed.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='install', choices=['install', 'restore'])
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--root', type=Path, default=Path('/'), help='system root for staging/testing')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--follow-user', help='follow this local account; defaults to the sudo caller')
    group.add_argument('--static', action='store_true', help='disable automatic matching and use Ichigo')
    args = parser.parse_args()
    try:
        user = args.follow_user or (os.environ.get('SUDO_USER') if not args.static else None)
        home = None
        if user:
            account = pwd.getpwnam(user)
            if account.pw_uid == 0: raise ValueError('Choose a regular desktop account')
            home = account.pw_dir
        apply(args.action, args.root, args.dry_run, home, args.static)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'bankai-login: {error}\n')

if __name__ == '__main__': main()
