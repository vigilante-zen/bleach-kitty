"""Snapshot restores roll back earlier writes and deletions on late failures."""
import importlib.machinery
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('bankai_backup', str(ROOT / 'desktop/python/bin/bankai-desktop-backup'))
spec = importlib.util.spec_from_loader(loader.name, loader)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class RestoreTransactionChecks(unittest.TestCase):
    def test_snapshot_creation_rejects_dangling_config_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            kitty = home / '.config/kitty/kitty.conf'
            kitty.parent.mkdir(parents=True)
            kitty.write_text('font_size 12\n')
            linked = home / '.config/kdeglobals'
            linked.symlink_to(home / 'missing-kdeglobals')
            root = home / 'Backups/Bleach-Desktop'
            with self.assertRaisesRegex(ValueError, 'Symlink cannot be backed up or restored'):
                backup.create(home, root)
            self.assertTrue(linked.is_symlink())
            self.assertFalse(any(path.is_dir() and (path / 'manifest.json').exists() for path in root.iterdir()))

    def test_executed_python_backup_command_includes_desktop_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            kitty = home / '.config/kitty/kitty.conf'
            globals_ = home / '.config/kdeglobals'
            kitty.parent.mkdir(parents=True)
            kitty.write_text('font_size 12\n')
            globals_.write_text('[General]\nColorScheme=BleachRukia\n')
            env = dict(os.environ, HOME=str(home))
            command = [sys.executable, str(ROOT / 'desktop/python/bin/bankai-desktop-backup')]
            subprocess.run(command, env=env, check=True, capture_output=True, text=True)

            snapshot_root = home / 'Backups/Bleach-Desktop'
            snapshots = [path for path in snapshot_root.iterdir() if path.is_dir() and (path / 'manifest.json').is_file()]
            self.assertEqual(len(snapshots), 1)
            manifest = json.loads((snapshots[0] / 'manifest.json').read_text())
            saved = {entry['path'] for entry in manifest['files']}
            self.assertIn('.config/kdeglobals', saved)

            globals_.write_text('[General]\nColorScheme=BreezeDark\n')
            added = home / '.config/fish/config.fish'
            added.parent.mkdir(parents=True)
            added.write_text('# added after snapshot\n')
            subprocess.run(command + ['restore', snapshots[0].name], env=env, check=True, capture_output=True, text=True)
            self.assertEqual(globals_.read_text(), '[General]\nColorScheme=BleachRukia\n')
            self.assertFalse(added.exists())

    def test_oversized_snapshot_manifest_is_rejected_before_json_parsing(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            snapshot = home / 'Backups/Bleach-Desktop/20261021-120000-000001'
            snapshot.mkdir(parents=True)
            (snapshot / 'manifest.json').write_bytes(b' ' * (backup.MAX_MANIFEST_BYTES + 1))
            with self.assertRaisesRegex(ValueError, '16 MiB size limit'):
                backup.verify_manifest(snapshot, home)

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
