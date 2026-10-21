"""Validate shared preference boundaries without changing the live desktop."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('appearance', ROOT / 'desktop/shared/appearance_settings.py')
appearance = importlib.util.module_from_spec(spec); spec.loader.exec_module(appearance)

class AppearanceChecks(unittest.TestCase):
    def test_native_and_shared_catalogs_match(self):
        native=json.loads((ROOT/'desktop/rust/assets/catalog.json').read_text())['presets']
        self.assertEqual(native, appearance.catalog())

    def test_defaults_never_write_and_valid_options_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            options = appearance.load(home)
            self.assertEqual(list(home.iterdir()), [])
            self.assertEqual(len(options['pool']), len(appearance.catalog()))
            options.update(edition='manga', accent='#aAbB12', login='renji', shuffle_login=True, pool=['renji'])
            appearance.save(home, options)
            self.assertEqual(appearance.load(home), options)
            self.assertEqual(appearance.shuffled(home, 'renji'), 'renji')
    def test_invalid_options_and_symlinks_preserve_saved_preferences(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder); options = appearance.defaults(); appearance.save(home, options)
            for key, invalid in [('edition','other'),('accent','#123'),('login',[]),('shuffle_login','true'),('pool',[]),('pool',['renji','renji'])]:
                with self.assertRaises(ValueError): appearance.save(home, dict(options, **{key:invalid}))
                self.assertEqual(appearance.load(home), options)
            path = home / '.local/share/bleach-desktop/appearance.json'; path.unlink()
            outside = home/'outside'; outside.write_text('unchanged'); path.symlink_to(outside)
            with self.assertRaises(ValueError): appearance.save(home, options)
            self.assertEqual(outside.read_text(),'unchanged')

    def test_stale_editor_cannot_replace_newer_shared_preferences(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder); expected=appearance.load(home)
            newer=dict(expected,edition='manga',accent='#123456',login='rukia')
            appearance.save(home,newer)
            stale=dict(expected,edition='manga',accent='#abcdef')
            with self.assertRaisesRegex(ValueError,'changed in another Bankai window'):
                appearance.save(home,stale,expected=expected)
            self.assertEqual(appearance.load(home),newer)

    def test_custom_presets_round_trip_and_delete(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder); options=appearance.defaults()
            options.update(edition='manga',accent='#aabbcc',login='rukia')
            row=appearance.save_custom_preset(home,'Night Rukia','rukia',options)
            self.assertEqual(row['preset'],'rukia')
            self.assertEqual(appearance.custom_presets(home),[row])
            with self.assertRaises(ValueError): appearance.save_custom_preset(home,'night rukia','ichigo',options)
            appearance.delete_custom_preset(home,row['id'])
            self.assertEqual(appearance.custom_presets(home),[])

if __name__ == '__main__': unittest.main()
