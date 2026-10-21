"""Snapshot restores roll back earlier writes and deletions on late failures."""
import importlib.machinery
import importlib.util
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('bankai_backup', str(ROOT / 'desktop/python/bin/bankai-desktop-backup'))
spec = importlib.util.spec_from_loader(loader.name, loader)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class RestoreTransactionChecks(unittest.TestCase):
    def test_boolean_manifest_version_is_not_accepted_as_integer_one(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            snapshot = home / 'Backups/Bleach-Desktop/20261021-120000-000001'
            source = snapshot / 'files/.config/kitty/config'
            source.parent.mkdir(parents=True)
            source.write_bytes(b'kitty config')
            (snapshot / 'manifest.json').write_text(json.dumps({
                'version': True,
                'files': [{'path': '.config/kitty/config', 'sha256': hashlib.sha256(b'kitty config').hexdigest(), 'mode': 0o600}],
                'absent': [],
            }))
            with self.assertRaisesRegex(ValueError, 'Invalid snapshot manifest'):
                backup.verify_manifest(snapshot, home)

    def test_late_failure_restores_replaced_deleted_files_and_modes(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            directory = home / '.config/kitty'
            directory.mkdir(parents=True)
            first = directory / 'restore-a'
            removed = directory / 'restore-b'
            last = directory / 'restore-c'
            first.write_text('first original')
            removed.write_text('removed original')
            last.write_text('last original')
            first.chmod(0o640)
            edits = {
                '.config/kitty/restore-a': (b'first replacement', 0o600),
                '.config/kitty/restore-b': None,
                '.config/kitty/restore-c': (b'last replacement', 0o600),
            }
            writes = 0

            def fail_second_write(path, contents, mode):
                nonlocal writes
                writes += 1
                if writes == 2:
                    raise OSError('injected restore failure')
                backup.atomic_write(path, contents, mode)

            with self.assertRaisesRegex(OSError, 'injected restore failure'):
                backup.restore_transaction(home, edits, fail_second_write)
            self.assertEqual(first.read_text(), 'first original')
            self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o640)
            self.assertEqual(removed.read_text(), 'removed original')
            self.assertEqual(last.read_text(), 'last original')


if __name__ == '__main__':
    unittest.main()
