"""Check cleanup against disposable snapshots; never remove real backups."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from snapshot_manager import BASELINE, MAX_MANIFEST_BYTES, SnapshotStore


class SnapshotManagementChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='bankai-snapshot-check-')
        self.home = Path(self.temporary.name)
        self.store = SnapshotStore(self.home / 'snapshots', self.home / 'state')
        self.names = [f'20261019-20000{i}-000000' for i in range(6)]
        for name in self.names + [BASELINE]:
            self.make_snapshot(name)

    def tearDown(self):
        self.temporary.cleanup()

    def make_snapshot(self, name):
        path = self.store.root / name
        (path / 'files/.config').mkdir(parents=True)
        (path / 'files/.config/example').write_text('snapshot payload')
        (path / 'manifest.json').write_text(json.dumps({'version': 1, 'files': [{'path': '.config/example'}]}))

    def test_sizes_count_actual_payload_and_manifest(self):
        row = self.store.scan()[0]
        path = self.store.root / row['name']
        expected = (path / 'files/.config/example').stat().st_size + (path / 'manifest.json').stat().st_size
        self.assertEqual(row['bytes'], expected)
        self.assertTrue(row['eligible'])

    def test_scans_and_previews_use_shared_snapshot_lock(self):
        with patch.object(self.store, 'locked', wraps=self.store.locked) as lock:
            self.store.scan()
            lock.assert_called_once_with()
        with patch.object(self.store, 'locked', wraps=self.store.locked) as lock:
            self.store.plan(keep=2)
            lock.assert_called_once_with()

    def test_store_rejects_symlinked_lock_file(self):
        self.store.state.mkdir(parents=True)
        outside = self.home / 'outside-lock'
        outside.write_text('preserve')
        (self.store.state / 'snapshot-management.lock').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'must not contain symlinks'):
            self.store.scan()
        self.assertEqual(outside.read_text(), 'preserve')

    def test_store_rejects_symlinked_snapshot_parent(self):
        target = self.home / 'real-snapshot-parent'
        target.mkdir()
        alias = self.home / 'snapshot-parent-alias'
        alias.symlink_to(target, target_is_directory=True)
        linked_store = SnapshotStore(alias / self.store.root.name, self.store.state)
        with self.assertRaisesRegex(ValueError, 'must not contain symlinks'):
            linked_store.scan()

    def test_backup_cli_rejects_symlinked_state_directory(self):
        home = self.home / 'cli-home'
        state_parent = home / '.local/state'
        state_parent.mkdir(parents=True)
        outside = self.home / 'outside-state'
        outside.mkdir()
        (state_parent / 'bleach-desktop').symlink_to(outside)
        script = Path(__file__).parent / 'bin/bankai-desktop-backup'
        env = os.environ.copy()
        env['HOME'] = str(home)
        result = subprocess.run([sys.executable, str(script), 'list'], env=env,
                                capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Symlink', result.stderr)
        self.assertFalse((outside / 'snapshot-management.lock').exists())

    def test_cleanup_keeps_newest_and_original_baseline(self):
        # The October baseline's timestamp is newer than these fixture snapshots.
        plan = self.store.plan(keep=2)
        protected = {BASELINE, self.names[-1]}
        self.assertTrue(protected.isdisjoint({r['name'] for r in plan['candidates']}))
        count, size = self.store.cleanup(plan)
        self.assertEqual(count, len(plan['candidates']))
        self.assertEqual(size, plan['bytes'])
        self.assertTrue(all((self.store.root / name).exists() for name in protected))

    def test_favorite_protection_is_persistent(self):
        name = self.names[0]
        self.store.protect(name)
        reopened = SnapshotStore(self.store.root, self.store.state)
        self.assertNotIn(name, {r['name'] for r in reopened.plan(1)['candidates']})
        reopened.protect(name, False)
        self.assertIn(name, {r['name'] for r in reopened.plan(1)['candidates']})
        with self.assertRaises(ValueError):
            self.store.protect(BASELINE, False)

    def test_protection_added_after_preview_cancels_every_deletion(self):
        plan = self.store.plan(1)
        self.store.protect(plan['candidates'][-1]['name'])
        with self.assertRaises(ValueError):
            self.store.cleanup(plan)
        self.assertTrue(all((self.store.root / r['name']).exists() for r in plan['candidates']))

    def test_file_changed_after_preview_cancels_every_deletion(self):
        plan = self.store.plan(1)
        target = self.store.root / plan['candidates'][-1]['name'] / 'files/.config/example'
        target.write_text('snapshot PAYLOAD')  # Same length, different content/mtime.
        with self.assertRaises(ValueError):
            self.store.cleanup(plan)
        self.assertTrue(all((self.store.root / r['name']).exists() for r in plan['candidates']))

    def test_extra_files_and_symlinks_are_never_cleanup_candidates(self):
        first, second = self.names[:2]
        (self.store.root / first / 'personal-file').write_text('keep me')
        outside = self.home / 'outside'
        outside.write_text('outside data')
        (self.store.root / second / 'files/link').symlink_to(outside)
        candidates = {r['name'] for r in self.store.plan(1)['candidates']}
        self.assertNotIn(first, candidates)
        self.assertNotIn(second, candidates)
        self.assertEqual(outside.read_text(), 'outside data')

    def test_unreadable_protections_block_cleanup(self):
        self.store.state.mkdir()
        (self.store.state / 'protected-snapshots.json').write_text('corrupt')
        with self.assertRaises(ValueError):
            self.store.plan(1)

    def test_oversized_manifest_is_ineligible_without_parsing(self):
        path = self.store.root / self.names[0] / 'manifest.json'
        path.write_bytes(b' ' * (16 * 1024 * 1024 + 1))
        row = next(item for item in self.store.scan() if item['name'] == self.names[0])
        self.assertFalse(row['eligible'])
        self.assertIn('16 MiB size limit', row['reason'])

    def test_manifest_read_is_bounded_to_limit_plus_one(self):
        class Reader:
            requested = None

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, size):
                self.requested = size
                return b'x' * size

        reader = Reader()
        manifest = self.store.root / self.names[0] / 'manifest.json'
        original_open = Path.open

        def open_manifest(path, *args, **kwargs):
            if path == manifest:
                return reader
            return original_open(path, *args, **kwargs)

        with patch('pathlib.Path.open', new=open_manifest):
            row = next(item for item in self.store.scan() if item['name'] == self.names[0])
        self.assertFalse(row['eligible'])
        self.assertEqual(reader.requested, MAX_MANIFEST_BYTES + 1)

    def test_scanner_rejects_boolean_versions_duplicate_and_noncanonical_paths(self):
        path = self.store.root / self.names[0] / 'manifest.json'
        original = json.loads(path.read_text())
        invalid_manifests = [
            {**original, 'version': True},
            {**original, 'files': original['files'] * 2},
            {**original, 'files': [{'path': './.config/example'}]},
        ]
        for manifest in invalid_manifests:
            with self.subTest(manifest=manifest):
                path.write_text(json.dumps(manifest))
                row = next(item for item in self.store.scan() if item['name'] == self.names[0])
                self.assertFalse(row['eligible'])
        path.write_text(json.dumps(original))

    def test_cannot_escape_snapshot_directory(self):
        plan = self.store.plan(1)
        plan['candidates'][0]['name'] = '../outside'
        with self.assertRaises(ValueError):
            self.store.cleanup(plan)
        with self.assertRaises(ValueError):
            self.store.protect('../outside')
        with self.assertRaises(ValueError):
            self.store.plan(0)

    def test_cleanup_keep_limit_matches_rust(self):
        self.assertEqual(self.store.plan(1000)['keep'], 1000)
        with self.assertRaisesRegex(ValueError, 'between 1 and 1000'):
            self.store.plan(1001)
        plan = self.store.plan(1)
        plan['keep'] = 1001
        with self.assertRaisesRegex(ValueError, 'between 1 and 1000'):
            self.store.cleanup(plan)
        self.assertTrue(all((self.store.root / name).exists() for name in self.names))


if __name__ == '__main__':
    unittest.main(verbosity=2)
