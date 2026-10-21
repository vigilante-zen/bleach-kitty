"""Check edition archive boundaries and checksums without copying large artwork."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
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
                         'login/ARTWORK.json', 'login/install.py', 'login/sync.py', 'login/greeter_preview.py', 'login/legacy-theme.json', 'login/README.md', 'login/preview.py', 'login/preview.png', 'login/theme/Main.qml', 'login/theme/assets/ichigo.png',
                         'desktop/install.py', 'desktop/README.md', 'desktop/shared/wallpapers/art.png',
                         'desktop/shared/color-schemes/BleachIchigo.colors', 'login/theme/assets/scene-ichigo.png',
                         'desktop/python/install.py', 'desktop/rust/install.py',
                         'desktop/rust/target/release/leaked', 'desktop/rust/bin/bankai-rust', 'desktop/python/__pycache__/leaked.pyc']:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('test')
            catalog = {'presets': [{'id': 'ichigo', 'title': 'Ichigo', 'subtitle': 'Ember',
                                    'accent': '#ff9d52', 'image': 'art.png', 'portrait': 'ichigo',
                                    'manga': 'ichigo-manga.png'}]}
            (root / 'desktop/shared/presets.json').write_text(json.dumps(catalog))
            png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + struct.pack('>II', 1, 1)
            (root / 'desktop/shared/wallpapers/art.png').write_bytes(png_header)
            (root / 'login/theme/assets/scene-ichigo.png').write_bytes(png_header)
            binary = Path(temp) / 'binary'; binary.write_bytes(b'compiled')
            with patch.object(packages, 'ROOT', root):
                for edition in ['python', 'rust']:
                    archive = packages.package(edition, Path(temp) / 'dist', binary if edition == 'rust' else None,
                                               'linux-x86-64' if edition == 'rust' else None)
                    with tarfile.open(archive) as tar:
                        names = tar.getnames()
                        self.assertTrue(any(name.endswith('/login/install.py') for name in names))
                        self.assertTrue(any(name.endswith('/login/theme/Main.qml') for name in names))
                        self.assertTrue(any(name.endswith('/login/theme/assets/ichigo.png') for name in names))
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

    def test_packaging_stops_when_preset_artwork_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'repo'; root.mkdir()
            catalog = {'presets': [{'id': 'ichigo', 'title': 'Ichigo', 'subtitle': 'Ember',
                                    'accent': '#ff9d52', 'image': 'ichigo.png', 'portrait': 'ichigo',
                                    'manga': 'ichigo-manga.png'}]}
            path = root / 'desktop/shared/presets.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(catalog))
            output = Path(temp) / 'dist'
            with patch.object(packages, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'Preset asset consistency check failed'):
                    packages.package('python', output)
            self.assertFalse(output.exists())

    def test_binary_platform_name_is_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                packages.package('rust', Path(temp), Path(temp) / 'binary', '../../escape')


if __name__ == '__main__':
    unittest.main()
