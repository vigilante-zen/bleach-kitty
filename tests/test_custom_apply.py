"""Custom preset failures must not leave shared appearance settings half-applied."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('bankai_desktop_cli', str(ROOT / 'desktop/python/bin/bankai-desktop'))
spec = importlib.util.spec_from_loader(loader.name, loader)
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)

class CustomApplyChecks(unittest.TestCase):
    def test_config_and_state_writes_roll_back_together(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            first = home / '.config/a-first'
            first.parent.mkdir(parents=True)
            first.write_text('original')
            first.chmod(0o640)
            (home / '.local/share/bleach-desktop').mkdir(parents=True)
            (home / '.local/share/bleach-desktop/current').write_text('old\n')
            (home / '.local/state/bleach-desktop').mkdir(parents=True)
            (home / '.local/state/bleach-desktop/pending').write_text('old pending\n')
            (home / '.local/share/bleach-desktop/appearance.json').write_text('old appearance\n')
            edits = {
                '.config/a-first': b'updated',
                '.config/z-second': b'new file',
                '.local/share/bleach-desktop/current': b'new preset\n',
                '.local/state/bleach-desktop/pending': b'new preset\n',
                '.local/share/bleach-desktop/appearance.json': b'new appearance\n',
                '.config/zz-last': b'failure trigger',
            }
            calls = 0
            def fail_after_appearance_write(path, contents, mode):
                nonlocal calls
                calls += 1
                if calls == 6: raise OSError('injected write failure')
                desktop.atomic_write(path, contents, mode)
            with self.assertRaisesRegex(OSError, 'injected write failure'):
                desktop.write_transaction(home, edits, fail_after_appearance_write)
            self.assertEqual(first.read_text(), 'original')
            self.assertEqual(first.stat().st_mode & 0o777, 0o640)
            self.assertFalse((home / '.config/z-second').exists())
            self.assertFalse((home / '.config/zz-last').exists())
            self.assertEqual((home / '.local/share/bleach-desktop/current').read_text(), 'old\n')
            self.assertEqual((home / '.local/state/bleach-desktop/pending').read_text(), 'old pending\n')
            self.assertEqual((home / '.local/share/bleach-desktop/appearance.json').read_text(), 'old appearance\n')
            external = home / 'external'; external.write_text('untouched')
            linked = home / '.config/z-linked'; linked.symlink_to(external)
            with self.assertRaisesRegex(ValueError, 'Linked appearance preferences'):
                desktop.write_transaction(home, {'.config/a-first': b'not applied', '.config/z-linked': b'not written'})
            self.assertEqual(first.read_text(), 'original')
            self.assertEqual(external.read_text(), 'untouched')
            self.assertTrue(linked.is_symlink())

    def test_missing_artwork_restores_previous_shared_options(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            old = {key: getattr(desktop, key) for key in ('HOME', 'DATA', 'STATE')}
            desktop.HOME = home
            desktop.DATA = home / '.local/share/bleach-desktop'
            desktop.STATE = home / '.local/state/bleach-desktop'
            try:
                original = desktop.appearance_settings.load(home)
                choices = dict(original, edition='manga', accent='#123456', login='rukia')
                row = desktop.appearance_settings.save_custom_preset(home, 'Missing Manga', 'rukia', choices)
                with self.assertRaisesRegex(ValueError, 'Wallpaper is missing'):
                    desktop.apply_custom(row['id'])
                self.assertEqual(desktop.appearance_settings.load(home), original)
                self.assertFalse((desktop.DATA / 'current').exists())
            finally:
                for key, value in old.items(): setattr(desktop, key, value)

    def test_custom_apply_snapshot_keeps_previous_appearance_options(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            old_globals = {key: getattr(desktop, key) for key in ('HOME', 'DATA', 'STATE')}
            desktop.HOME = home
            desktop.DATA = home / '.local/share/bleach-desktop'
            desktop.STATE = home / '.local/state/bleach-desktop'
            try:
                previous = desktop.appearance_settings.defaults()
                previous.update(edition='manga', accent='#123456', login='ichigo')
                desktop.appearance_settings.save(home, previous)
                row = desktop.appearance_settings.save_custom_preset(home, 'Rukia color', 'rukia', {
                    **previous, 'edition': 'color', 'accent': '#abcdef', 'login': 'rukia',
                })
                preset = next(p for p in desktop.appearance_settings.catalog() if p['id'] == 'rukia')
                wallpapers = home / 'Pictures/Bleach-TYBW/Wallpapers'
                wallpapers.mkdir(parents=True)
                shutil.copy(ROOT / 'desktop/shared/wallpapers' / preset['image'], wallpapers / preset['image'])
                schemes = home / '.local/share/color-schemes'
                schemes.mkdir(parents=True)
                shutil.copy(ROOT / 'desktop/shared/color-schemes' / 'BleachRukia.colors', schemes / 'BleachRukia.colors')
                config = home / '.config'
                (config / 'kitty').mkdir(parents=True)
                (config / 'kitty/kitty.conf').write_text('font_size 12\n')
                (config / 'kdeglobals').write_text('[General]\n')
                (config / 'plasma-org.kde.plasma.desktop-appletsrc').write_text('[Containments][1]\nplugin=org.kde.plasma.folder\n')

                snapshot = home / 'safety-snapshot'
                def fake_run(args):
                    if args[0].endswith('bankai-desktop-backup'):
                        saved = snapshot / 'files/.local/share/bleach-desktop/appearance.json'
                        saved.parent.mkdir(parents=True)
                        shutil.copy(desktop.DATA / 'appearance.json', saved)
                        return SimpleNamespace(returncode=0, stdout='backup complete')
                    return SimpleNamespace(returncode=1, stdout='')

                with patch.object(desktop, 'run', side_effect=fake_run):
                    desktop.apply_custom(row['id'])
                backup_options = json.loads((snapshot / 'files/.local/share/bleach-desktop/appearance.json').read_text())
                self.assertEqual(backup_options, previous)
                self.assertEqual(desktop.appearance_settings.load(home)['accent'], '#abcdef')
                self.assertEqual((desktop.DATA / 'current').read_text(), 'rukia\n')
            finally:
                for key, value in old_globals.items(): setattr(desktop, key, value)

if __name__ == '__main__': unittest.main()
