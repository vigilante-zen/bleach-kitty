"""Check cleanup against disposable snapshots; never remove real backups."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from snapshot_manager import BASELINE, SnapshotStore


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

    def test_cannot_escape_snapshot_directory(self):
        plan = self.store.plan(1)
        plan['candidates'][0]['name'] = '../outside'
        with self.assertRaises(ValueError):
            self.store.cleanup(plan)
        with self.assertRaises(ValueError):
            self.store.protect('../outside')
        with self.assertRaises(ValueError):
            self.store.plan(0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
