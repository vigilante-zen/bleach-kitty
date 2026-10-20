"""Character additions are usable in complete rotation and their proper groups."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / 'files/.local/bin/bankai-roster'
NEW = {'nemu', 'askin', 'lille', 'yachiru'}


class CharacterRosterChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bankai-roster-check-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        portraits = self.home / '.config/fastfetch/portraits'; portraits.mkdir(parents=True)
        for source in (ROOT / 'files/.config/fastfetch/portraits').glob('*.png'):
            (portraits / source.name).touch()
        self.env = dict(os.environ, HOME=str(self.home), XDG_STATE_HOME=str(self.home / '.local/state'))
        self.roster = types.ModuleType('roster_checks')
        exec(compile(ROSTER.read_text(), str(ROSTER), 'exec'), self.roster.__dict__)

    def command(self, *args):
        return subprocess.run([sys.executable, str(ROSTER), *args], env=self.env,
                              capture_output=True, text=True, check=True).stdout

    def test_balanced_rotation_includes_all_36_characters_once(self):
        self.command('shuffle', 'character')
        selected = [Path(self.command('next').strip()).stem for _ in range(36)]
        owners = [self.roster.CHARACTER_OWNER.get(name, name) for name in selected]
        self.assertEqual(len(set(owners)), 36)
        self.assertTrue(NEW <= set(owners))

    def test_new_arrivals_and_faction_groups_include_new_characters(self):
        self.command('group', 'new-arrivals')
        selected = {Path(self.command('next').strip()).stem for _ in self.roster.GROUPS['new-arrivals']}
        self.assertEqual(selected, set(self.roster.GROUPS['new-arrivals']))
        self.assertTrue(NEW <= selected)
        self.assertTrue({'nemu', 'yachiru'} <= set(self.roster.GROUPS['soul-reapers']))
        self.assertTrue({'askin', 'lille'} <= set(self.roster.GROUPS['quincy']))
        catalog = self.command('catalog')
        for name in NEW:
            self.assertIn(name + '\t' + self.roster.DISPLAY_NAMES[name], catalog)

    def test_new_pairs_are_valid_distinct_square_pngs_with_recorded_hashes(self):
        records = json.loads((ROOT / 'docs/prompts/additions-20261020/PROMPTS.json').read_text())
        self.assertEqual({record['id'] for record in records['characters']}, NEW)
        for character in records['characters']:
            sizes = []
            hashes = []
            for edition in ['color', 'manga']:
                info = character['editions'][edition]
                data = (ROOT / info['path']).read_bytes()
                self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
                width, height = struct.unpack('>II', data[16:24])
                self.assertEqual(width, height); self.assertGreaterEqual(width, 1024)
                sizes.append((width, height))
                sha = hashlib.sha256(data).hexdigest()
                self.assertEqual(sha, info['sha256']); hashes.append(sha)
            self.assertEqual(sizes[0], sizes[1]); self.assertNotEqual(hashes[0], hashes[1])


if __name__ == '__main__':
    unittest.main()
