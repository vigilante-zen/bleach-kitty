"""The shared appearance catalog and its installable assets stay in sync."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('check_presets', ROOT / 'scripts/check_presets.py')
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class PresetAssetChecks(unittest.TestCase):
    def test_current_roster_is_complete(self):
        self.assertEqual(checker.validate(ROOT), [])

    def test_missing_preset_assets_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for source in ['desktop/shared/presets.json', 'desktop/shared/wallpapers',
                           'desktop/shared/color-schemes', 'login/theme/assets']:
                destination = root / source
                if (ROOT / source).is_dir():
                    import shutil
                    shutil.copytree(ROOT / source, destination)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes((ROOT / source).read_bytes())
            (root / 'desktop/shared/wallpapers/nelliel-desktop.png').unlink()
            errors = checker.validate(root)
            self.assertTrue(any('nelliel' in error and 'image artwork' in error for error in errors))


if __name__ == '__main__':
    unittest.main()
