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
