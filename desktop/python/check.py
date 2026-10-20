"""Isolated checks for desktop presets and snapshot integrity."""
from pathlib import Path
import importlib.machinery
import importlib.util
import json
import shutil
import subprocess
import tempfile

def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

h = Path.home()
desktop = load('desktop_test', h / '.local/bin/bankai-desktop')
backup = load('backup_test', h / '.local/bin/bankai-desktop-backup')
with tempfile.TemporaryDirectory(prefix='bleach-desktop-check-') as tmp:
    home = Path(tmp)
    (home / '.config').mkdir()
    target = home / '.config/kdeglobals'
    target.write_text('original\n')
    snap, count = backup.create(home, home / 'snapshots')
    target.write_text('changed\n')
    missing = home / '.config/autostart/bleach-desktop.desktop'
    missing.parent.mkdir()
    missing.write_text('new\n')
    entries = backup.verify(snap, home)
    for rel in json.loads((snap / 'manifest.json').read_text()).get('absent', []):
        (home / rel).unlink(missing_ok=True)
    for entry in entries:
        dest = home / entry['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snap / 'files' / entry['path'], dest)
    assert target.read_text() == 'original\n' and not missing.exists()
    (snap / 'files/.config/kdeglobals').write_text('corrupted')
    try:
        backup.verify(snap, home)
    except ValueError:
        pass
    else:
        raise AssertionError('Corruption was accepted')
    desktop.HOME = home
    desktop.DATA = home / '.local/share/bleach-desktop'
    desktop.DATA.mkdir(parents=True)
    desktop.STATE = home / '.local/state/bleach-desktop'
    for rel in ['.local/share/color-schemes', 'Pictures/Bleach-TYBW/Wallpapers',
                '.config/fastfetch', '.config/kitty/themes']:
        (home / rel).mkdir(parents=True, exist_ok=True)
    for p in (h / '.local/share/color-schemes').glob('Bleach*.colors'):
        shutil.copy2(p, home / '.local/share/color-schemes' / p.name)
    for key in desktop.PRESETS:
        name = 'bleach-tybw.png' if key == 'tybw' else key + '-desktop.png'
        (home / 'Pictures/Bleach-TYBW/Wallpapers' / name).write_bytes(b'test asset')
    (home / '.config/kitty/kitty.conf').write_text('font_size 12\n')
    shutil.copy2(h / '.config/plasma-org.kde.plasma.desktop-appletsrc',
                 home / '.config/plasma-org.kde.plasma.desktop-appletsrc')
    desktop.run = lambda args: None
    for name, (_, portrait, accent) in desktop.PRESETS.items():
        desktop.apply(name, pending_only=True)
        assert (home / '.config/fastfetch/portrait-choice').read_text().strip() == portrait
        assert (desktop.STATE / 'pending').read_text().strip() == name
    assert (home / '.config/kitty/kitty.conf').read_text().count('include themes/bleach-desktop.conf') == 1
    text = (home / '.config/plasma-org.kde.plasma.desktop-appletsrc').read_text()
    assert text.count('Image=file://' + str(home)) == 2
    desktop.run = lambda args: subprocess.CompletedProcess(args, 0, '', '')
    desktop.apply('rukia', pending_only=True)
    assert not (desktop.STATE / 'pending').exists()
print('PASS: snapshot restore, absent-file cleanup, corruption rejection, all presets, two screens, idempotent include, refresh completion.')
