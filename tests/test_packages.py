"""Check edition archive boundaries and checksums without copying large artwork."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('edition_packages', Path(__file__).resolve().parents[1] / 'scripts/package_editions.py')
packages = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packages)


class PackageChecks(unittest.TestCase):
    def test_archives_include_only_selected_edition_and_no_build_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'repo'; root.mkdir()
            for name in ['install.py', 'MANIFEST.json', 'LICENSE', 'files/.config/theme', 'docs/ARTWORK.md',
                         'desktop/install.py', 'desktop/README.md', 'desktop/shared/wallpapers/art.png',
                         'desktop/python/install.py', 'desktop/rust/install.py',
                         'desktop/rust/target/release/leaked', 'desktop/rust/bin/bankai-rust', 'desktop/python/__pycache__/leaked.pyc']:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('test')
            binary = Path(temp) / 'binary'; binary.write_bytes(b'compiled')
            with patch.object(packages, 'ROOT', root):
                for edition in ['python', 'rust']:
                    archive = packages.package(edition, Path(temp) / 'dist', binary if edition == 'rust' else None,
                                               'linux-x86-64' if edition == 'rust' else None)
                    with tarfile.open(archive) as tar:
                        names = tar.getnames()
                        other = 'python' if edition == 'rust' else 'rust'
                        self.assertFalse(any('/desktop/' + other + '/' in name for name in names))
                        self.assertFalse(any('target/' in name or '__pycache__/' in name for name in names))
                        entry = next(name for name in names if name.endswith('/PACKAGE.json'))
                        metadata = json.load(tar.extractfile(entry))
                        self.assertEqual(metadata['edition'], edition)
                        self.assertEqual(metadata['prebuilt'], edition == 'rust')
                        if edition == 'rust':
                            executable = tar.getmember(archive.name[:-7] + '/desktop/rust/bin/bankai-rust')
                            self.assertEqual(executable.mode & 0o777, 0o755)
                    expected = archive.with_suffix(archive.suffix + '.sha256').read_text().split()[0]
                    self.assertEqual(expected, hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_binary_platform_name_is_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                packages.package('rust', Path(temp), Path(temp) / 'binary', '../../escape')


if __name__ == '__main__':
    unittest.main()
