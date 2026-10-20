import importlib.util
import json
import os
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('login_install', ROOT / 'login/install.py')
login = importlib.util.module_from_spec(spec); spec.loader.exec_module(login)

class LoginInstallChecks(unittest.TestCase):
    def test_staged_lifecycle_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prior = root / 'etc/sddm.conf.d/kde_settings.conf'
            prior.parent.mkdir(parents=True); prior.write_text('[Theme]\nCurrent=breeze\n')
            login.apply('install', root, True)
            self.assertFalse((root / 'usr').exists())
            login.apply('install', root)
            login.apply('install', root)
            self.assertTrue((root / 'usr/share/sddm/themes/bankai-manga/Main.qml').is_file())
            login.apply('restore', root)
            self.assertEqual(prior.read_text(), '[Theme]\nCurrent=breeze\n')
            self.assertFalse((root / 'etc/sddm.conf.d/zz-bankai-manga.conf').exists())
            self.assertFalse((root / 'usr/share/sddm/themes/bankai-manga').exists())

    def test_exact_standalone_theme_can_migrate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); login.apply('install', root)
            receipt = root / 'var/lib/bankai-login/receipt.json'
            receipt.unlink()
            login.apply('install', root)
            self.assertTrue(receipt.is_file())
            receipt.unlink()
            qml = root / 'usr/share/sddm/themes/bankai-manga/Main.qml'
            qml.write_text('customized')
            with self.assertRaises(ValueError): login.apply('install', root)

    def test_edited_theme_blocks_update_and_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); login.apply('install', root)
            qml = root / 'usr/share/sddm/themes/bankai-manga/Main.qml'; qml.write_text('edited')
            for action in ['install', 'restore']:
                with self.assertRaises(ValueError): login.apply(action, root)
            self.assertEqual(qml.read_text(), 'edited')

    def test_follow_updates_from_both_marker_write_patterns(self):
        spec = importlib.util.spec_from_file_location('login_sync', ROOT / 'login/sync.py')
        sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'system'; home = Path(temp) / 'home'
            marker = home / '.local/share/bleach-desktop/current'
            marker.parent.mkdir(parents=True); marker.write_text('rukia\n')
            login.apply('install', root, home=home)
            selected = root / login.DYNAMIC
            self.assertEqual(selected.read_bytes(), sync.selection('rukia'))
            marker.write_text('byakuya\n')  # Python edition writes in place.
            self.assertTrue(sync.sync(root))
            replacement = marker.with_suffix('.new'); replacement.write_text('ulquiorra\n')
            os.replace(replacement, marker)  # Rust edition replaces atomically.
            self.assertTrue(sync.sync(root))
            self.assertEqual(selected.read_bytes(), sync.selection('ulquiorra'))
            for invalid in ['../../etc/passwd', 'ichigo\nCharacter=rukia', 'x' * 100]:
                marker.write_text(invalid)
                self.assertFalse(sync.sync(root))
                self.assertEqual(selected.read_bytes(), sync.selection('ulquiorra'))
            settings = marker.parent / 'appearance.json'
            settings.write_text(json.dumps({'login': 'yhwach'}))
            self.assertTrue(sync.sync(root))
            self.assertEqual(selected.read_bytes(), sync.selection('yhwach'))
            settings.unlink()
            marker.unlink(); marker.symlink_to('/etc/passwd')
            self.assertFalse(sync.sync(root))
            login.apply('install', root)  # Preserve follow settings across update.
            self.assertIn(str(home), (root / login.FOLLOW).read_text())
            login.apply('restore', root)
            self.assertFalse((root / login.WATCH).exists())
            self.assertFalse((root / login.SERVICE).exists())

    def test_watcher_paths_are_absolute_without_literal_quotes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'system'
            home = Path(temp) / 'home with spaces%'
            login.apply('install', root, home=home)
            paths = [line.removeprefix('PathChanged=') for line in
                     (root / login.WATCH).read_text().splitlines()
                     if line.startswith('PathChanged=')]
            self.assertEqual(paths, [str(home).replace('%', '%%') + suffix for suffix in
                ('/.local/share/bleach-desktop/current',
                 '/.local/share/bleach-desktop/appearance.json')])
            self.assertTrue(all(path.startswith('/') for path in paths))

    def test_legacy_standalone_theme_can_upgrade(self):
        # The currently installed original theme has no receipt.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / login.PREFIX
            for name in json.loads((ROOT / 'login/legacy-theme.json').read_text()):
                path = target / name; path.parent.mkdir(parents=True, exist_ok=True)
                fixture = ROOT / 'tests/fixtures/login-v1' / name
                source = fixture if fixture.is_file() else ROOT / 'login/theme' / name
                data = source.read_bytes()
                path.write_bytes(data)
            config = root / login.CONFIG_PATH; config.parent.mkdir(parents=True); config.write_bytes(login.CONFIG)
            login.apply('install', root)
            self.assertTrue((target / 'assets/scene-rukia.png').is_file())
            login.apply('restore', root)

    def test_failed_write_rolls_back_and_allows_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = login.atomic
            def fail_once(path, data):
                if path.name == 'receipt.json': raise OSError('simulated disk error')
                return original(path, data)
            with patch.object(login, 'atomic', side_effect=fail_once):
                with self.assertRaises(OSError): login.apply('install', root)
            self.assertFalse((root / login.PREFIX).exists())
            self.assertFalse((root / login.CONFIG_PATH).exists())
            login.apply('install', root)
            login.apply('restore', root)

    def test_static_mode_removes_follow_units(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'system'; home = Path(temp) / 'home'; home.mkdir()
            login.apply('install', root, home=home)
            login.apply('install', root, static=True)
            self.assertFalse((root / login.WATCH).exists())
            self.assertFalse((root / login.SERVICE).exists())
            self.assertFalse((root / login.FOLLOW).exists())
            self.assertFalse((root / login.DYNAMIC).exists())
            login.apply('restore', root)

    def test_unmanaged_and_symlink_destinations_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'etc').symlink_to('/tmp')
            with self.assertRaises(ValueError): login.apply('install', root)

if __name__ == '__main__': unittest.main()
