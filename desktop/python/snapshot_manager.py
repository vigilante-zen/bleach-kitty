"""Inspect and protect Bankai snapshots; delete only an explicitly reviewed plan."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

BASELINE = '20261019-202424-204727'
NAME = re.compile(r'^\d{8}-\d{6}-\d{6}$')
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_KEEP = 1000


def format_size(size):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if size < 1024 or unit == 'TiB':
            return f'{size:.1f} {unit}'
        size /= 1024


def read_manifest(path):
    with path.open('rb') as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError('Snapshot manifest exceeds the 16 MiB size limit.')
    return raw


def reject_symlinks(path):
    path = Path(os.path.abspath(path))
    for boundary in (path, *path.parents):
        if boundary.is_symlink():
            raise ValueError(f'Snapshot storage path must not contain symlinks: {boundary}')


class SnapshotStore:
    def __init__(self, root=None, state=None):
        home = Path.home()
        self.root = Path(root) if root is not None else home / 'Backups/Bleach-Desktop'
        self.state = Path(state) if state is not None else home / '.local/state/bleach-desktop'

    @contextmanager
    def locked(self, wait=True):
        reject_symlinks(self.root)
        reject_symlinks(self.state)
        self.state.mkdir(parents=True, exist_ok=True)
        lock_path = self.state / 'snapshot-management.lock'
        reject_symlinks(lock_path)
        with lock_path.open('a') as stream:
            operation = fcntl.LOCK_EX if wait else fcntl.LOCK_EX | fcntl.LOCK_NB
            fcntl.flock(stream, operation)
            yield

    def protections(self):
        path = self.state / 'protected-snapshots.json'
        if not path.exists():
            return set()
        if path.is_symlink():
            raise ValueError('Snapshot protection metadata must not be a symlink.')
        data = json.loads(path.read_text())
        if not isinstance(data, list) or any(not isinstance(name, str) or not NAME.fullmatch(name) for name in data):
            raise ValueError('Snapshot protection metadata is unreadable; cleanup is disabled.')
        return set(data)

    def protect(self, name, enabled=True):
        if not isinstance(name, str) or not NAME.fullmatch(name):
            raise ValueError('Invalid snapshot name.')
        with self.locked(wait=False):
            path = self.root / name
            if path.is_symlink() or not path.is_dir() or not (path / 'manifest.json').is_file():
                raise ValueError('The snapshot could not be found.')
            if name == BASELINE and not enabled:
                raise ValueError('The original restore baseline always stays protected.')
            names = self.protections()
            if enabled:
                names.add(name)
            else:
                names.discard(name)
            fd, temporary = tempfile.mkstemp(prefix='.protected-', dir=self.state)
            try:
                with os.fdopen(fd, 'w') as stream:
                    json.dump(sorted(names), stream)
                    stream.write('\n')
                os.replace(temporary, self.state / 'protected-snapshots.json')
            finally:
                Path(temporary).unlink(missing_ok=True)

    def scan(self):
        with self.locked(wait=False):
            return self._scan()

    def _scan(self):
        if self.root.is_symlink():
            raise ValueError('The snapshot directory must not be a symlink.')
        protected = self.protections()
        rows = []
        if not self.root.exists():
            return rows
        for path in sorted(self.root.iterdir(), reverse=True):
            if path.name.startswith('.') or path.is_symlink() or not path.is_dir():
                continue
            manifest = path / 'manifest.json'
            if not manifest.is_file() or manifest.is_symlink():
                continue
            row = {'name': path.name, 'bytes': 0, 'files': 0, 'protected': path.name in protected or path.name == BASELINE,
                   'baseline': path.name == BASELINE, 'eligible': False, 'reason': ''}
            try:
                raw = read_manifest(manifest)
                data = json.loads(raw)
                entries = data.get('files') if isinstance(data, dict) else None
                if (type(data.get('version')) is not int or data['version'] != 1
                        or not isinstance(entries, list) or not entries):
                    raise ValueError('Snapshot metadata is invalid.')
                expected = {'manifest.json'}
                seen = set()
                for entry in entries:
                    relative = entry.get('path') if isinstance(entry, dict) else None
                    relative_path = Path(relative) if isinstance(relative, str) else None
                    if (relative_path is None or not relative or relative_path.is_absolute()
                            or str(relative_path) != relative
                            or any(part in ('', '.', '..') for part in relative.split('/'))
                            or relative in seen):
                        raise ValueError('Snapshot paths are invalid.')
                    seen.add(relative)
                    expected.add('files/' + relative)
                row['files'] = len(entries)
                actual = set()
                tree_hash = hashlib.sha256()
                for parent, dirs, files in os.walk(path, followlinks=False):
                    dirs.sort()
                    files.sort()
                    for item in dirs + files:
                        child = Path(parent) / item
                        info = child.lstat()
                        if stat.S_ISLNK(info.st_mode):
                            raise ValueError('Contains symlinks; review manually.')
                        if stat.S_ISREG(info.st_mode):
                            row['bytes'] += info.st_size
                            relative = str(child.relative_to(path))
                            actual.add(relative)
                            tree_hash.update(json.dumps([relative, info.st_ino, info.st_size, info.st_mtime_ns]).encode())
                        elif not stat.S_ISDIR(info.st_mode):
                            raise ValueError('Contains special files; review manually.')
                if actual != expected:
                    raise ValueError('Contains missing or additional files; review manually.')
                if not NAME.fullmatch(path.name):
                    raise ValueError('Unrecognized snapshot name; review manually.')
                info = path.stat()
                row['fingerprint'] = [info.st_dev, info.st_ino, info.st_mtime_ns, hashlib.sha256(raw).hexdigest(), tree_hash.hexdigest(), row['bytes']]
                row['eligible'] = True
            except (OSError, ValueError, TypeError, AttributeError) as error:
                row['reason'] = str(error)
            rows.append(row)
        return rows

    def plan(self, keep=5):
        if type(keep) is not int or not 1 <= keep <= MAX_KEEP:
            raise ValueError(f'Keep between 1 and {MAX_KEEP} snapshots.')
        with self.locked(wait=False):
            return self._plan(keep)

    def _plan(self, keep):
        rows = self._scan()
        # Keep the most recent usable snapshots, plus every protected snapshot.
        newest = {row['name'] for row in [r for r in rows if r['eligible']][:keep]}
        candidates = [row for row in rows if row['eligible'] and not row['protected'] and row['name'] not in newest]
        return {'version': 1, 'keep': keep, 'candidates': candidates,
                'bytes': sum(row['bytes'] for row in candidates)}

    def cleanup(self, plan):
        if not isinstance(plan, dict) or plan.get('version') != 1 or not isinstance(plan.get('candidates'), list):
            raise ValueError('Invalid cleanup plan.')
        keep = plan.get('keep')
        if type(keep) is not int or not 1 <= keep <= MAX_KEEP:
            raise ValueError(f'Keep between 1 and {MAX_KEEP} snapshots.')
        with self.locked():
            current = {row['name']: row for row in self._plan(keep)['candidates']}
            reviewed = plan['candidates']
            seen = set()
            # Validate every target before removing any snapshot.
            for row in reviewed:
                if not isinstance(row, dict):
                    raise ValueError('Invalid cleanup target.')
                name = row.get('name')
                if not isinstance(name, str) or not NAME.fullmatch(name) or name in seen:
                    raise ValueError('Invalid cleanup target.')
                seen.add(name)
                if name not in current or row.get('fingerprint') != current[name]['fingerprint']:
                    raise ValueError('Snapshots or protections changed. Preview cleanup again.')
            for row in reviewed:
                shutil.rmtree(self.root / row['name'])
            return len(reviewed), sum(current[row['name']]['bytes'] for row in reviewed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['cleanup'])
    parser.add_argument('--plan', required=True, help='Exact JSON cleanup plan reviewed in Bankai')
    args = parser.parse_args()
    try:
        count, size = SnapshotStore().cleanup(json.loads(args.plan))
        print(f'Removed {count} old snapshots ({format_size(size)}).')
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f'Cleanup cancelled: {error}\n')


if __name__ == '__main__':
    main()
