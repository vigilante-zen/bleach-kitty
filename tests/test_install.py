import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('installer', REPO / 'install.py')
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class InstallationTests(unittest.TestCase):
    def run_installer(self, home, *args, ok=True):
        result = subprocess.run([sys.executable, str(REPO / 'install.py'), *args, '--home', str(home)], capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_payload_integrity_and_no_private_paths(self):
        manifest = json.loads((REPO / 'MANIFEST.json').read_text())
        actual = {str(p.relative_to(REPO / 'files')) for p in (REPO / 'files').rglob('*') if p.is_file()}
        self.assertEqual(set(manifest), actual)
        for name, expected in manifest.items():
            data = (REPO / 'files' / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected, name)
            self.assertLess(len(data), 100 * 1024 * 1024)
            if not name.endswith('.png'):
                self.assertNotIn(b'/home/zen', data, name)
        self.assertEqual(len(list((REPO / 'files/.config/fastfetch/portraits').glob('*.png'))), 40)
        self.assertEqual(len(list((REPO / 'files/.config/fastfetch/manga').glob('*.png'))), 40)

    def test_install_relocate_and_restore(self):
        with tempfile.TemporaryDirectory(prefix='bankai home ') as temp:
            home = Path(temp)
            kitty = home / '.config/kitty/kitty.conf'
            kitty.parent.mkdir(parents=True)
            kitty.write_text('font_size 13\n')
            choice = home / '.config/fastfetch/portrait-choice'
            choice.parent.mkdir(parents=True)
            choice.write_text('urahara\n')
            prompt = home / '.config/fish/functions/fish_prompt.fish'
            prompt.parent.mkdir(parents=True)
            prompt.write_text('function fish_prompt; echo original; end\n')
            self.run_installer(home, '--dry-run')
            self.assertFalse((home / '.local').exists())
            self.run_installer(home)
            self.assertEqual(choice.read_text(), 'urahara\n')
            self.assertTrue(kitty.read_text().startswith('font_size 13\n'))
            monitor = (home / '.config/btop/portraits/urahara.conf').read_text()
            self.assertIn(str(home / '.config/btop/portraits/urahara.theme'), monitor)
            self.assertTrue((home / '.local/bin/bankai-roster').stat().st_mode & 0o111)
            self.run_installer(home, ok=False)
            self.run_installer(home, 'uninstall')
            self.assertEqual(kitty.read_text(), 'font_size 13\n')
            self.assertEqual(prompt.read_text(), 'function fish_prompt; echo original; end\n')
            self.assertEqual(choice.read_text(), 'urahara\n')
            self.assertFalse((home / '.config/fastfetch/portraits/urahara.png').exists())

    def test_uninstall_preserves_later_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            self.run_installer(home)
            kitty = home / '.config/kitty/kitty.conf'
            with kitty.open('a') as stream:
                stream.write('font_size 17\n')
            prompt = home / '.config/fish/functions/fish_prompt.fish'
            prompt.write_text('# user edit\n')
            self.run_installer(home, 'uninstall')
            self.assertEqual(kitty.read_text(), 'font_size 17\n')
            self.assertEqual(prompt.read_text(), '# user edit\n')
            self.assertTrue((home / '.local/state/bleach-kitty-install/receipt.json').exists())

    def test_symlink_destination_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / 'home'
            home.mkdir()
            outside = Path(temp) / 'outside'
            outside.mkdir()
            (home / '.config').symlink_to(outside)
            self.run_installer(home, ok=False)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse((home / '.local').exists())


if __name__ == '__main__':
    unittest.main()
