#!/usr/bin/env python3
"""Exercise the compiled Rust app against disposable homes and Python snapshots."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
BINARY = PROJECT / 'target/release/bankai-rust'
CATALOG = json.loads((PROJECT / 'assets/catalog.json').read_text())
backup_source = PROJECT.parent / 'python/bin/bankai-desktop-backup'
if not backup_source.is_file():
    backup_source = Path.home() / '.local/bin/bankai-desktop-backup'
loader = importlib.machinery.SourceFileLoader('python_backup', str(backup_source))
spec = importlib.util.spec_from_loader(loader.name, loader)
python_backup = importlib.util.module_from_spec(spec)
loader.exec_module(python_backup)


class CompiledRustChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='bankai-rust-binary-')
        self.home = Path(self.temporary.name)
        self.root = self.home / 'Backups/Bleach-Desktop'
        self.state = self.home / '.local/state/bleach-desktop'
        self.env = dict(os.environ, BANKAI_HOME=str(self.home))
        self.write('.config/kitty/kitty.conf', 'font_size 12\n')
        self.write('.config/kdeglobals', '[General]\nUnrelated=preserved\n')
        self.write('.config/plasma-org.kde.plasma.desktop-appletsrc',
                   '[Containments][202]\nplugin=org.kde.plasma.folder\n\n'
                   '[Containments][202][Wallpaper][org.kde.image][General]\nImage=old\n\n'
                   '[Containments][203]\nplugin=org.kde.plasma.folder\n')
        for preset in CATALOG['presets']:
            self.write('Pictures/Bleach-TYBW/Wallpapers/' + preset['image'], 'test wallpaper')
            self.write('.local/share/color-schemes/Bleach' + preset['title'] + '.colors',
                       '[Colors:Window]\nForegroundNormal=232,237,245\n')

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, relative, text):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def rpc(self, op, fail=False, **kwargs):
        process = subprocess.run([str(BINARY), '--rpc'], input=json.dumps(dict(op=op, **kwargs)),
                                 text=True, capture_output=True, env=self.env, timeout=30)
        reply = json.loads(process.stdout)
        if fail:
            self.assertNotEqual(process.returncode, 0)
            self.assertFalse(reply['ok'])
            return reply['error']
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertTrue(reply['ok'], reply)
        return reply['result']

    def test_python_and_rust_desktop_catalogs_match(self):
        shared_path = PROJECT.parent / 'shared/appearance_settings.py'
        spec = importlib.util.spec_from_file_location('shared_appearance', shared_path)
        appearance = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(appearance)
        self.assertEqual(CATALOG['presets'], appearance.catalog())

    def snapshot(self, name=None):
        created = self.rpc('backup')['name']
        if name:
            (self.root / created).rename(self.root / name)
            return name
        return created

    def test_rust_hashes_and_manifest_match_python(self):
        name = self.snapshot()
        manifest = json.loads((self.root / name / 'manifest.json').read_text())
        for entry in manifest['files']:
            path = self.root / name / 'files' / entry['path']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry['sha256'])
        verified = python_backup.verify(self.root / name, self.home)
        self.assertEqual(len(verified), len(manifest['files']))

    def test_rust_restores_python_snapshot_and_permissions(self):
        target = self.home / '.config/kitty/kitty.conf'
        target.chmod(0o640)
        snapshot, _ = python_backup.create(self.home, self.root)
        target.write_text('changed')
        added = self.write('.config/fish/completions/bankai.fish', 'new')
        result = self.rpc('restore', name=snapshot.name)
        self.assertEqual(target.read_text(), 'font_size 12\n')
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        self.assertFalse(added.exists())
        self.assertTrue((self.root / result['previous']).exists())

    def test_python_restores_rust_snapshot(self):
        name = self.snapshot()
        target = self.home / '.config/kitty/kitty.conf'
        target.write_text('changed')
        environment = dict(os.environ, HOME=str(self.home))
        process = subprocess.run(['python3', str(backup_source), 'restore', name],
                                 text=True, capture_output=True, env=environment, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(target.read_text(), 'font_size 12\n')

    def test_corruption_cancels_restore_before_changes(self):
        name = self.snapshot()
        path = self.root / name / 'files/.config/kitty/kitty.conf'
        path.write_text('corruption')
        active = self.write('.config/kitty/kitty.conf', 'keep active settings')
        self.rpc('restore', name=name, fail=True)
        self.assertEqual(active.read_text(), 'keep active settings')

    def test_symlink_destination_is_rejected(self):
        name = self.snapshot()
        outside = self.write('outside', 'untouched')
        target = self.home / '.config/kitty/kitty.conf'
        target.unlink()
        target.symlink_to(outside)
        self.rpc('restore', name=name, fail=True)
        self.assertEqual(outside.read_text(), 'untouched')

    def test_traversal_manifest_is_rejected(self):
        name = self.snapshot()
        manifest = self.root / name / 'manifest.json'
        data = json.loads(manifest.read_text())
        data['files'][0]['path'] = '../../outside'
        manifest.write_text(json.dumps(data))
        self.rpc('restore', name=name, fail=True)

    def test_all_eighteen_presets_are_native_and_update_both_screens(self):
        for preset in CATALOG['presets']:
            result = self.rpc('apply', preset=preset['id'])
            self.assertTrue(result['pending'])
            self.assertEqual((self.home / '.local/share/bleach-desktop/current').read_text().strip(), preset['id'])
            self.assertFalse((self.home / '.config/fastfetch/portrait-choice').exists())
            settings = (self.home / '.config/plasma-org.kde.plasma.desktop-appletsrc').read_text()
            self.assertEqual(settings.count('Image=file://'), 2)
        self.assertEqual((self.home / '.config/kitty/kitty.conf').read_text().count('include themes/bleach-desktop.conf'), 1)
        self.assertIn('Unrelated=preserved', (self.home / '.config/kdeglobals').read_text())

    def test_portrait_preferences_survive_desktop_switches(self):
        self.write('.config/fastfetch/portraits/urahara.png', 'test image')
        self.assertEqual(self.rpc('portraits')['portraits'], ['urahara'])
        for choice, art in [('random', 'mixed'), ('urahara', 'manga'), ('random', 'color')]:
            self.rpc('save-portraits', choice=choice, art=art)
            self.rpc('apply', preset='ichigo')
            state = self.rpc('portraits')
            self.assertEqual((state['choice'], state['art']), (choice, art))
        for choice, art in [('../outside', 'color'), ('missing', 'color'), ('random', 'bad')]:
            self.rpc('save-portraits', choice=choice, art=art, fail=True)
        self.assertEqual(self.rpc('portraits')['art'], 'color')

    def test_shared_appearance_manga_accent_and_login_shuffle(self):
        spec = importlib.util.spec_from_file_location('shared_appearance', PROJECT.parent / 'shared/appearance_settings.py')
        appearance = importlib.util.module_from_spec(spec); spec.loader.exec_module(appearance)
        options = appearance.defaults()
        options.update(edition='manga', accent='#123456', login='yhwach', shuffle_login=True, pool=['renji', 'hitsugaya'])
        appearance.save(self.home, options)
        self.assertEqual(self.rpc('appearance'), options)
        for name in options['pool']: self.write('Pictures/Bleach-TYBW/Wallpapers/' + name + '-manga.png', 'manga wallpaper')
        self.rpc('apply', preset='renji')
        self.assertIn('renji-manga.png', (self.home / '.config/kscreenlockerrc').read_text())
        self.assertIn('AccentColor=18,52,86', (self.home / '.config/kdeglobals').read_text())
        self.rpc('shuffle-login')
        self.assertEqual(self.rpc('status')['current'], 'hitsugaya')
        self.rpc('save-appearance', appearance=dict(options, shuffle_login=False))
        self.assertFalse(appearance.load(self.home)['shuffle_login'])
        for bad in [dict(options, edition='other'), dict(options, accent='#123'), dict(options, pool=[]), dict(options, login='../bad')]:
            self.rpc('save-appearance', appearance=bad, fail=True)
        self.assertFalse(appearance.load(self.home)['shuffle_login'])

    def test_match_desktop_can_be_enabled_and_disabled(self):
        self.write('.config/fastfetch/portraits/ichigo-tybw.png', 'test image')
        self.write('.config/fastfetch/portraits/rukia-bankai.png', 'test image')
        self.rpc('apply', preset='ichigo')
        self.rpc('save-portraits', choice='random', art='mixed', match_desktop=True)
        self.assertEqual(self.rpc('portraits')['choice'], 'ichigo-tybw')
        self.rpc('apply', preset='rukia')
        state = self.rpc('portraits')
        self.assertTrue(state['match_desktop'])
        self.assertEqual((state['choice'], state['art']), ('rukia-bankai', 'mixed'))
        self.rpc('apply', preset='tybw')
        self.assertEqual(self.rpc('portraits')['choice'], 'random')
        self.rpc('save-portraits', choice='random', art='manga', match_desktop=False)
        self.rpc('apply', preset='ichigo')
        state = self.rpc('portraits')
        self.assertFalse(state['match_desktop'])
        self.assertEqual((state['choice'], state['art']), ('random', 'manga'))

    def test_portrait_symlink_does_not_modify_external_file(self):
        target = self.write('outside-art', 'untouched')
        path = self.home / '.config/fastfetch/portrait-art-mode'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
        self.rpc('save-portraits', choice='random', art='manga', fail=True)
        self.assertEqual(target.read_text(), 'untouched')

    def test_missing_asset_keeps_active_settings(self):
        (self.home / 'Pictures/Bleach-TYBW/Wallpapers/urahara-desktop.png').unlink()
        self.rpc('apply', preset='urahara', fail=True)
        self.assertFalse((self.home / '.local/share/bleach-desktop/current').exists())

    def test_cleanup_retains_newest_baseline_and_favorites(self):
        for i in range(5):
            self.snapshot(f'20261019-22000{i}-000000')
        baseline = '20261019-202424-204727'
        self.snapshot(baseline)
        favorite = '20261019-220000-000000'
        self.rpc('protect', name=favorite, enabled=True)
        plan = self.rpc('plan', keep=2)
        self.assertEqual(len(plan['candidates']), 2)
        self.rpc('cleanup', plan=plan)
        for name in [baseline, favorite, '20261019-220003-000000', '20261019-220004-000000']:
            self.assertTrue((self.root / name).exists())
        self.rpc('protect', name=baseline, enabled=False, fail=True)

    def test_post_review_protection_cancels_every_deletion(self):
        for i in range(3):
            self.snapshot(f'20261019-22000{i}-000000')
        plan = self.rpc('plan', keep=1)
        self.rpc('protect', name=plan['candidates'][-1]['name'], enabled=True)
        self.rpc('cleanup', plan=plan, fail=True)
        self.assertEqual(len(list(self.root.iterdir())), 3)

    def test_post_review_file_changes_cancel_every_deletion(self):
        for i in range(3):
            self.snapshot(f'20261019-22000{i}-000000')
        plan = self.rpc('plan', keep=1)
        target = self.root / plan['candidates'][-1]['name'] / 'files/.config/kitty/kitty.conf'
        target.write_text('font_size 99\n')
        self.rpc('cleanup', plan=plan, fail=True)
        self.assertEqual(len(list(self.root.iterdir())), 3)

    def test_extra_files_and_symlinks_are_kept(self):
        names = [self.snapshot(f'20261019-22000{i}-000000') for i in range(3)]
        (self.root / names[0] / 'personal-file').write_text('preserve')
        (self.root / names[1] / 'link').symlink_to(self.home / '.config/kdeglobals')
        self.assertEqual(self.rpc('plan', keep=1)['candidates'], [])

    def test_bad_protections_disable_cleanup(self):
        self.write('.local/state/bleach-desktop/protected-snapshots.json', 'corrupt')
        self.rpc('plan', keep=1, fail=True)

    def test_autostart_affects_only_rust_edition(self):
        existing = self.write('.config/autostart/bleach-bankai.desktop', 'python startup')
        self.rpc('autostart', enabled=True)
        rust = self.home / '.config/autostart/bleach-bankai-rust.desktop'
        self.assertIn('bankai-rust', rust.read_text())
        self.rpc('autostart', enabled=False)
        self.assertFalse(rust.exists())
        self.assertEqual(existing.read_text(), 'python startup')

    def test_invalid_rpc_and_cleanup_keep_are_rejected(self):
        self.rpc('plan', keep=0, fail=True)
        self.rpc('unknown', fail=True)
        process = subprocess.run([str(BINARY), '--rpc'], input='{"op":"status","op":"backup"}',
                                 capture_output=True, text=True, env=self.env)
        self.assertNotEqual(process.returncode, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
