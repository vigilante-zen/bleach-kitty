"""Desktop installer ownership, rollback, backup and confinement checks."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('desktop_install', Path(__file__).resolve().parents[1] / 'desktop/install.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class DesktopInstallerChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.state = self.home / '.local/state/bankai-desktop-install'
        self.shared = '.local/share/bleach-desktop/README.md'
        self.python = '.local/bin/bankai'
        self.rust = '.local/bin/bankai-rust'

    def change(self, edition, action='install', files=None, dry=False):
        installer.change(edition, action, self.home, self.state, files or {}, dry)

    def test_two_editions_keep_shared_files_until_last_uninstall(self):
        for edition, binary in [('python', self.python), ('rust', self.rust)]:
            self.change(edition, files={self.shared: (b'shared', 0o644), binary: (b'exe', 0o755)})
        self.change('python', 'uninstall')
        self.assertTrue((self.home / self.shared).exists())
        self.assertTrue((self.home / self.rust).exists())
        self.assertFalse((self.home / self.python).exists())
        self.change('rust', 'uninstall')
        self.assertFalse((self.home / self.shared).exists())

    def test_upgrade_restores_original_and_preserves_mode(self):
        path = self.home / self.python
        path.parent.mkdir(parents=True)
        path.write_bytes(b'original'); path.chmod(0o700)
        self.change('python', files={self.python: (b'v1', 0o755)})
        self.change('python', files={self.python: (b'v2', 0o755)})
        self.change('python', 'uninstall')
        self.assertEqual(path.read_bytes(), b'original')
        self.assertEqual(path.stat().st_mode & 0o777, 0o700)

    def test_modified_files_are_kept_and_block_updates(self):
        self.change('python', files={self.python: (b'app', 0o755)})
        (self.home / self.python).write_bytes(b'my changes')
        with self.assertRaises(ValueError):
            self.change('python', files={self.python: (b'update', 0o755)})
        self.change('python', 'uninstall')
        self.assertEqual((self.home / self.python).read_bytes(), b'my changes')
        self.assertIn(self.python, json.loads((self.state / 'receipt.json').read_text())['files'])

    def test_dry_run_writes_nothing(self):
        self.change('python', files={self.python: (b'app', 0o755)}, dry=True)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_symlinks_and_receipt_traversal_are_rejected(self):
        outside = self.home / 'outside'; outside.write_text('untouched')
        path = self.home / self.python; path.parent.mkdir(parents=True); path.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.change('python', files={self.python: (b'app', 0o755)})
        self.assertEqual(outside.read_text(), 'untouched')
        self.state.mkdir(parents=True)
        (self.state / 'receipt.json').write_text(json.dumps({'version': 1, 'files': {'../../outside': {}}}))
        with self.assertRaises(ValueError):
            self.change('python', 'uninstall')

    def test_receipt_failure_rolls_back_files(self):
        original = installer.atomic
        def fail_receipt(path, *args):
            if path.name == 'receipt.json':
                raise OSError('simulated disk error')
            return original(path, *args)
        with patch.object(installer, 'atomic', side_effect=fail_receipt):
            with self.assertRaises(OSError):
                self.change('python', files={self.python: (b'app', 0o755)})
        self.assertFalse((self.home / self.python).exists())

    def test_real_edition_payloads_have_launchers_and_no_preferences(self):
        executable = self.home / 'compiled'; executable.write_bytes(b'compiled')
        for edition in ['python', 'rust']:
            files = installer.payload(edition, self.home, executable)
            self.assertTrue(any(name.endswith('.desktop') for name in files))
            self.assertFalse(any('portrait-choice' in name or 'autostart' in name for name in files))
            self.change(edition, files=files)
        self.change('rust', 'uninstall')
        self.assertTrue((self.home / self.python).is_file())
        self.change('python', 'uninstall')


if __name__ == '__main__':
    unittest.main()
