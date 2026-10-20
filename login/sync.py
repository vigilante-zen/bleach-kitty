#!/usr/bin/env python3
"""Select bundled login art from a bounded desktop preset marker; run by systemd."""
import json
import os
from pathlib import Path
import stat
import tempfile

PRESETS = ('ichigo', 'rukia', 'quincy', 'tybw', 'urahara', 'byakuya', 'yamamoto', 'ulquiorra', 'renji', 'hitsugaya', 'kenpachi', 'yhwach')
THEME_PATH = 'usr/share/sddm/themes/bankai-manga'

def selection(preset):
    if preset not in PRESETS:
        raise ValueError('Unknown desktop preset')
    return f'[General]\nCharacter={preset}\n'.encode()

def read_preset(home):
    path = Path(home) / '.local/share/bleach-desktop/current'
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode): return None
        value = os.read(fd, 65)
        if len(value) > 64: return None
        preset = value.decode('ascii').strip()
        return preset if preset in PRESETS else None
    except (UnicodeError, OSError):
        return None
    finally:
        os.close(fd)

def login_preset(home):
    path = Path(home) / '.local/share/bleach-desktop/appearance.json'
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode): return read_preset(home)
            data = os.read(fd, 8193)
        finally: os.close(fd)
        if len(data) <= 8192:
            value = json.loads(data)
            if isinstance(value, dict) and value.get('login') in PRESETS: return value['login']
    except (OSError, ValueError, TypeError): pass
    return read_preset(home)

def sync(root=Path('/'), home=None):
    root = Path(root)
    if home is None:
        home = json.loads((root / 'var/lib/bankai-login/follow.json').read_text())['home']
    preset = login_preset(home)
    if preset is None:
        print('No valid desktop preset; keeping the previous login scene.')
        return False
    path = root / THEME_PATH / 'theme.conf.user'
    if path.is_symlink(): raise ValueError('Refusing a linked login configuration')
    data = selection(preset)
    if path.exists() and path.read_bytes() == data: return False
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream: stream.write(data)
        os.chmod(name, 0o644)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
    print(f'Login scene follows desktop: {preset}')
    return True

if __name__ == '__main__': sync()
