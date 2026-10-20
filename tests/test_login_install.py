import importlib.util
from pathlib import Path
import tempfile
import unittest

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

    def test_unmanaged_and_symlink_destinations_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'etc').symlink_to('/tmp')
            with self.assertRaises(ValueError): login.apply('install', root)

if __name__ == '__main__': unittest.main()
