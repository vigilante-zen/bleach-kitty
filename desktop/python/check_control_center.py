"""Exercise the control center offscreen without changing the real desktop."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImageReader

SOURCE = Path(__file__).parent / 'control_center.py'
REPO = SOURCE.parents[2]
spec = importlib.util.spec_from_file_location('bankai_control_center', SOURCE)
center = importlib.util.module_from_spec(spec)
spec.loader.exec_module(center)
app = QApplication.instance() or QApplication([])
app.setStyle('Fusion')
app.setStyleSheet(center.STYLE)


class ControlCenterChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='bankai-ui-check-')
        self.home = Path(self.temporary.name)
        self.original = {key: getattr(center, key) for key in ['HOME', 'DATA', 'SNAPSHOTS', 'WALLPAPERS']}
        center.HOME = self.home
        center.DATA = self.home / '.local/share/bleach-desktop'
        center.DATA.mkdir(parents=True)
        (center.DATA / 'current').write_text('ichigo\n')
        center.SNAPSHOTS = self.home / 'snapshots'
        center.WALLPAPERS = REPO / 'desktop/shared/wallpapers'
        snapshot = center.SNAPSHOTS / '20261019-123456-123456'
        snapshot.mkdir(parents=True)
        (snapshot / 'manifest.json').write_text(json.dumps({'version': 1, 'files': [{'path': 'example'}]}))
        self.window = center.ControlCenter()
        self.window.show()
        app.processEvents()

    def tearDown(self):
        self.assertIsNone(self.window.process, 'A test left an action running')
        self.window.close()
        self.window.deleteLater()
        app.processEvents()
        for key, value in self.original.items():
            setattr(center, key, value)
        self.temporary.cleanup()

    def wait_for_action(self):
        deadline = time.monotonic() + 5
        while self.window.process is not None and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        app.processEvents()
        self.assertIsNone(self.window.process)

    def test_previews_do_not_change_saved_preset(self):
        for name in center.PRESETS:
            self.window.cards[name].click()
            self.assertEqual(self.window.selected, name)
            self.assertFalse(self.window.art.pixmap.isNull())
            self.assertLessEqual(self.window.art.pixmap.width(), 1600)
            self.assertLessEqual(self.window.art.pixmap.height(), 1000)
        self.assertEqual((center.DATA / 'current').read_text(), 'ichigo\n')

    def test_apply_uses_the_selected_preset(self):
        commands = []
        self.window.run_task = lambda *args: commands.append(args)
        self.window.select_preset('rukia')
        self.window.apply_preset()
        self.assertEqual(commands[0][0], [str(center.BIN / 'bankai-desktop'), 'rukia'])

    def test_custom_preset_can_be_saved_previewed_applied_and_deleted(self):
        original = center.QInputDialog.getText
        center.QInputDialog.getText = staticmethod(lambda *args, **kwargs: ('Night Ichigo', True))
        try:
            self.window.save_custom_preset()
            self.assertEqual(self.window.custom_combo.count(), 1)
            self.assertEqual(self.window.custom_rows[0]['preset'], 'ichigo')
            self.window.preview_custom_preset(0)
            self.assertIn('Night Ichigo', self.window.message.text())
            commands = []
            self.window.run_task = lambda *args: commands.append(args)
            self.window.apply_custom_preset()
            self.assertEqual(commands[0][0], [str(center.BIN / 'bankai-desktop'), 'apply-custom', self.window.custom_rows[0]['id']])
            self.window.delete_custom_preset()
            self.assertEqual(self.window.custom_combo.count(), 0)
        finally:
            center.QInputDialog.getText = original

    def test_custom_preset_file_size_is_bounded(self):
        path = center.DATA / 'custom-presets.json'
        path.write_bytes(b' ' * (center.appearance_settings.MAX_CUSTOM_PRESET_BYTES + 1))
        with self.assertRaisesRegex(ValueError, '64 KiB size limit'):
            center.appearance_settings.custom_presets(self.home)

    def test_custom_preset_fifo_is_rejected_without_reading(self):
        path = center.DATA / 'custom-presets.json'
        os.mkfifo(path)
        with self.assertRaisesRegex(ValueError, 'regular file'):
            center.appearance_settings.custom_presets(self.home)

    def test_custom_presets_refresh_after_external_edits_without_losing_selection(self):
        self.window.setup_tray(show=False)
        options = center.appearance_settings.defaults()
        first = center.appearance_settings.save_custom_preset(self.home, 'Night Ichigo', 'ichigo', options)
        deadline = time.monotonic() + 3
        while self.window.custom_combo.count() != 1 and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        self.assertEqual(self.window.custom_combo.itemData(0), first['id'])
        self.window.custom_combo.setCurrentIndex(0)

        second = center.appearance_settings.save_custom_preset(self.home, 'Manga Rukia', 'rukia',
            dict(options, edition='manga'))
        deadline = time.monotonic() + 3
        while self.window.custom_combo.count() != 2 and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        self.assertEqual(self.window.custom_combo.count(), 2)
        self.assertEqual(self.window.custom_combo.currentData(), first['id'])

        center.appearance_settings.delete_custom_preset(self.home, first['id'])
        deadline = time.monotonic() + 3
        while self.window.custom_combo.count() != 1 and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        self.assertEqual(self.window.custom_combo.currentData(), second['id'])

    def test_corrupt_appearance_preferences_are_reported_without_opening_editor(self):
        path = center.HOME / '.local/share/bleach-desktop/appearance.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{ invalid json')
        answers = [center.QMessageBox.StandardButton.No,
                   center.QMessageBox.StandardButton.Yes]
        original = center.QMessageBox.question
        center.QMessageBox.question = staticmethod(lambda *args: answers.pop(0))
        try:
            self.window.appearance_options()
            self.assertEqual(path.read_text(), '{ invalid json')
            self.window.appearance_options()
        finally:
            center.QMessageBox.question = original
        self.assertEqual(center.appearance_settings.load(center.HOME), center.appearance_settings.defaults())
        backups = list(path.parent.glob('appearance.json.corrupt-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), '{ invalid json')
        self.assertIn('preserved as', self.window.message.text())

    def test_ultrawide_wallpapers_match_monitor_aspect(self):
        for name in ['urahara', 'byakuya', 'yamamoto', 'ulquiorra']:
            size = QImageReader(str(center.WALLPAPERS / center.PRESETS[name][3])).size()
            self.assertGreater(size.height(), 0, name)
            # Generated assets can vary by a few pixels while retaining the ultrawide composition.
            self.assertLess(abs(size.width() / size.height() - 2560 / 1080), .01, name)

    def test_small_window_can_reach_all_presets(self):
        self.window.resize(900, 650)
        app.processEvents()
        for name in center.PRESETS:
            card = self.window.cards[name]
            self.window.appearance_scroll.ensureWidgetVisible(card)
            app.processEvents()
            self.assertTrue(card.isVisible())
            card.click()
            self.assertEqual(self.window.selected, name)

    def test_restore_cancel_does_nothing(self):
        commands = []
        self.window.run_task = lambda *args: commands.append(args)
        self.window.confirm_restore = lambda: False
        self.window.restore_snapshot()
        self.assertEqual(commands, [])
        self.window.confirm_restore = lambda: True
        self.window.restore_snapshot()
        self.assertEqual(commands[0][0], [str(center.BIN / 'bankai-desktop-backup'), 'restore',
                                         '20261019-123456-123456'])

    def test_successful_action_runs_without_blocking_and_prevents_close(self):
        self.window.run_task([sys.executable, '-c', 'print("snapshot complete")'], 'Working', 'Saved')
        self.assertIsNotNone(self.window.process)
        self.assertFalse(self.window.close())
        self.assertTrue(all(not button.isEnabled() for button in self.window.action_buttons))
        self.wait_for_action()
        self.assertIn('snapshot complete', self.window.output)
        self.assertEqual(self.window.message.text(), 'Saved')
        self.assertTrue(all(button.isEnabled() for button in self.window.action_buttons))

    def test_failed_action_exposes_output(self):
        self.window.run_task([sys.executable, '-c', 'import sys; print("bad snapshot"); sys.exit(3)'],
                             'Working', 'Saved')
        self.wait_for_action()
        self.assertIn('bad snapshot', self.window.output)
        self.assertIn('did not finish successfully', self.window.message.text())
        self.assertTrue(self.window.log.isVisible())

    def test_missing_command_reports_start_failure(self):
        self.window.run_task([str(self.home / 'missing-command')], 'Working', 'Saved')
        self.wait_for_action()
        self.assertIn('did not finish successfully', self.window.message.text())
        self.assertTrue(self.window.output)

    def test_empty_and_corrupt_snapshot_lists(self):
        manifest = center.SNAPSHOTS / '20261019-123456-123456/manifest.json'
        manifest.write_text('not json')
        self.window.refresh_snapshots()
        self.assertIn('could not be read', self.window.snapshot_details.text())
        manifest.unlink()
        self.window.refresh_snapshots()
        self.assertEqual(self.window.snapshots.count(), 0)
        self.assertFalse(self.window.restore_button.isEnabled())
        self.assertFalse(self.window.verify_button.isEnabled())

    def test_snapshot_refresh_reports_busy_lock_without_waiting(self):
        state = self.home / '.local/state/bleach-desktop'
        state.mkdir(parents=True, exist_ok=True)
        selected = self.window.snapshots.currentData()
        with (state / 'snapshot-management.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                self.window.refresh_snapshots()
                self.assertIn('updating snapshots', self.window.storage_summary.text())
                self.assertEqual(self.window.snapshots.count(), 1)
                self.assertEqual(self.window.snapshots.currentData(), selected)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def test_tray_routes_every_preset_and_tracks_saved_selection(self):
        calls = []
        self.window.run_task = lambda *args: calls.append(args)
        self.window.setup_tray(show=False)
        self.assertEqual(set(self.window.preset_actions), set(center.PRESETS))
        self.assertTrue(self.window.preset_actions['ichigo'].isChecked())
        for name, action in self.window.preset_actions.items():
            action.trigger()
            self.assertEqual(calls[-1][0], [str(center.BIN / 'bankai-desktop'), name])
        self.assertEqual((center.DATA / 'current').read_text(), 'ichigo\n')

    def test_mask_changes_only_the_character_markings(self):
        for name, (_, _, accent, _) in center.PRESETS.items():
            icon = center.hollow_icon(accent)
            self.assertFalse(icon.isNull(), name)
            image = icon.pixmap(64, 64).toImage()
            self.assertEqual(image.pixelColor(32, 54).name(), accent, name)
            self.assertEqual(image.pixelColor(20, 20).name(), '#e8d6b2', name)

    def test_tray_follows_cli_changes_and_atomic_replacements(self):
        self.window.setup_tray(show=False)
        original_key = self.window.tray.icon().cacheKey()
        current = center.DATA / 'current'
        for name, atomic in [('byakuya', False), ('ulquiorra', True), ('quincy', False)]:
            if atomic:
                temporary = current.with_suffix('.new')
                temporary.write_text(name + '\n')
                temporary.replace(current)
            else:
                current.write_text(name + '\n')
            deadline = time.monotonic() + 3
            while self.window.tray_icon_preset != name and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.01)
            self.assertEqual(self.window.tray_icon_preset, name)
            self.assertNotEqual(self.window.tray.icon().cacheKey(), original_key)
            self.assertTrue(self.window.preset_actions[name].isChecked())

    def test_login_startup_can_be_enabled_and_disabled(self):
        path = self.home / '.config/autostart/bleach-bankai.desktop'
        self.window.set_autostart(True)
        self.assertIn('.local/bin/bankai-python tray\n', path.read_text())
        self.window.set_autostart(False)
        self.assertFalse(path.exists())

    def test_cleanup_preview_never_deletes_without_confirmation(self):
        plan = {'version': 1, 'keep': 5, 'candidates': [{'name': 'example'}], 'bytes': 100}
        self.window.store.plan = lambda keep: plan
        calls = []
        self.window.run_task = lambda *args: calls.append(args)
        self.window.confirm_cleanup = lambda reviewed: False
        self.window.preview_cleanup()
        self.assertEqual(calls, [])
        self.window.confirm_cleanup = lambda reviewed: True
        self.window.preview_cleanup()
        self.assertEqual(calls[-1][0][2:4], ['cleanup', '--plan'])
        self.assertEqual(json.loads(calls[-1][0][4]), plan)

    def test_snapshot_protection_changes_the_selected_snapshot(self):
        self.window.toggle_protection()
        row = self.window.snapshot_rows[self.window.snapshots.currentData()]
        self.assertTrue(row['protected'])
        self.window.toggle_protection()
        row = self.window.snapshot_rows[self.window.snapshots.currentData()]
        self.assertFalse(row['protected'])

    def test_second_instance_forwards_to_the_first(self):
        state = self.home / 'ipc'
        first = center.InstanceCoordinator(state)
        second = center.InstanceCoordinator(state)
        received = []
        first.callback = received.append
        try:
            try:
                started = first.start()
            except OSError as error:
                self.skipTest('Local sockets unavailable in this environment: ' + str(error))
            self.assertTrue(started)
            self.assertFalse(second.start())
            for index, message in enumerate(('backups', 'open', 'tray'), start=1):
                self.assertTrue(second.forward(message))
                deadline = time.monotonic() + 2
                while len(received) < index and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.01)
                self.assertEqual(received, list(('backups', 'open', 'tray')[:index]))
        finally:
            first.close()

    def test_instance_coordinator_rejects_symlinked_state_and_lock_paths(self):
        outside = self.home / 'outside-instance-state'
        outside.mkdir()
        alias = self.home / 'instance-state-alias'
        alias.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'must not contain symlinks'):
            center.InstanceCoordinator(alias)

        state = self.home / 'instance-state'
        state.mkdir()
        outside_file = self.home / 'outside-instance-lock'
        outside_file.write_text('keep')
        (state / 'bankai-control.lock').symlink_to(outside_file)
        with self.assertRaisesRegex(ValueError, 'must not contain symlinks'):
            center.InstanceCoordinator(state)
        (state / 'bankai-control.lock').unlink()
        (state / 'bankai-control.sock').symlink_to(outside_file)
        with self.assertRaisesRegex(ValueError, 'must not contain symlinks'):
            center.InstanceCoordinator(state)
        self.assertEqual(outside_file.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main(verbosity=2)
