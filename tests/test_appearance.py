"""Validate shared preference boundaries without changing the live desktop."""
import importlib.util
import fcntl
import json
from pathlib import Path
import tempfile
import threading
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

    def test_repair_preserves_malformed_preferences_and_refuses_to_reset_valid_state(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder); path=home/'.local/share/bleach-desktop/appearance.json'
            path.parent.mkdir(parents=True); path.write_text('not valid json\n')
            result=appearance.repair(home)
            self.assertEqual(appearance.load(home),appearance.defaults())
            backup=Path(result['backup'])
            self.assertEqual(backup.read_text(),'not valid json\n')
            current=dict(appearance.defaults(),edition='manga',accent='#123456',login='rukia')
            appearance.save(home,current)
            with self.assertRaisesRegex(ValueError,'readable again'):
                appearance.repair(home)
            self.assertEqual(appearance.load(home),current)
            path.unlink(); external=home/'external-appearance.json'; external.write_text('keep me')
            path.symlink_to(external)
            with self.assertRaisesRegex(ValueError,'Linked appearance preferences'):
                appearance.repair(home)
            self.assertEqual(external.read_text(),'keep me')
            self.assertTrue(path.is_symlink())

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

    def test_custom_preset_writes_wait_for_the_shared_state_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder); state=home/'.local/state/bleach-desktop'; state.mkdir(parents=True)
            lock=(state/'snapshot-management.lock').open('a')
            fcntl.flock(lock,fcntl.LOCK_EX)
            started=threading.Event(); finished=threading.Event(); errors=[]
            def save():
                started.set()
                try: appearance.save_custom_preset(home,'Concurrent Rukia','rukia',appearance.defaults())
                except Exception as error: errors.append(error)
                finally: finished.set()
            worker=threading.Thread(target=save)
            try:
                worker.start()
                self.assertTrue(started.wait(2))
                self.assertFalse(finished.wait(.1), 'custom preset write bypassed the shared Rust/snapshot lock')
            finally:
                fcntl.flock(lock,fcntl.LOCK_UN); lock.close()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors,[])
            self.assertEqual([row['name'] for row in appearance.custom_presets(home)],['Concurrent Rukia'])

if __name__ == '__main__': unittest.main()
