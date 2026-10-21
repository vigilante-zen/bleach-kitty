"""Custom preset failures must not leave shared appearance settings half-applied."""
import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest

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
            edits = {
                '.config/a-first': b'updated',
                '.config/z-second': b'new file',
                '.local/share/bleach-desktop/current': b'new preset\n',
                '.local/state/bleach-desktop/pending': b'new preset\n',
            }
            calls = 0
            def fail_fourth(path, contents, mode):
                nonlocal calls
                calls += 1
                if calls == 4: raise OSError('injected write failure')
                desktop.atomic_write(path, contents, mode)
            with self.assertRaisesRegex(OSError, 'injected write failure'):
                desktop.write_transaction(home, edits, fail_fourth)
            self.assertEqual(first.read_text(), 'original')
            self.assertEqual(first.stat().st_mode & 0o777, 0o640)
            self.assertFalse((home / '.config/z-second').exists())
            self.assertEqual((home / '.local/share/bleach-desktop/current').read_text(), 'old\n')
            self.assertEqual((home / '.local/state/bleach-desktop/pending').read_text(), 'old pending\n')
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

if __name__ == '__main__': unittest.main()
