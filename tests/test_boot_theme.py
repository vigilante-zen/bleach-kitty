"""Validate Plymouth syntax and the boot installer's staging/rollback behavior."""
import ctypes
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('boot_install',ROOT/'boot/install.py')
boot=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(boot)


class BootThemeChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='bankai-boot-check-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.destination,self.config,self.state=boot.locations(self.root)
        self.config.parent.mkdir(parents=True)
        self.original=b'# Original settings\n[Daemon]\nTheme=details\nShowDelay=2\n'
        self.config.write_bytes(self.original)
        (self.root/'etc/mkinitcpio.conf').write_text('HOOKS=(base systemd plymouth filesystems)\n')
        (self.root/'etc/default').mkdir()
        (self.root/'etc/default/limine').write_text('ESP_PATH="/boot"\n')

    def test_staged_install_update_and_restore_original(self):
        boot.perform(self.root,'install','silhouette')
        self.assertEqual(boot.theme_name(self.config.read_text()),boot.NAME)
        self.assertIn('variant_mode = "silhouette";', (self.destination/'bankai.script').read_text())
        self.assertEqual(boot.rebuild_command(self.root),['/usr/bin/limine-mkinitcpio'])
        boot.perform(self.root,'install','silhouette')
        self.assertEqual((self.state/'original.conf').read_bytes(),self.original)
        self.assertIn('variant_mode = "silhouette";', (self.destination/'bankai.script').read_text())
        boot.perform(self.root,'remove','silhouette')
        self.assertEqual(self.config.read_bytes(),self.original)
        self.assertFalse(self.destination.exists())

    def test_removal_preserves_other_config_edits(self):
        boot.perform(self.root,'install','silhouette')
        self.config.write_text(self.config.read_text().replace('ShowDelay=2','ShowDelay=3'))
        boot.perform(self.root,'remove','silhouette')
        self.assertEqual(boot.theme_name(self.config.read_text()),'details')
        self.assertIn('ShowDelay=3',self.config.read_text())

    def test_modified_theme_blocks_update_and_removal(self):
        boot.perform(self.root,'install','silhouette')
        (self.destination/'bankai.script').write_text('locally edited')
        for action in ['install','remove']:
            with self.assertRaises(ValueError):boot.prepare(self.root,action,'silhouette')
        self.assertEqual((self.destination/'bankai.script').read_text(),'locally edited')

    def test_rebuild_failure_restores_previous_configuration(self):
        with patch.object(boot.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['test-rebuild'])) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                boot.perform(self.root,'install','silhouette',rebuild=True)
            self.assertEqual(run.call_count,2)
        self.assertEqual(self.config.read_bytes(),self.original)
        self.assertFalse(self.destination.exists())
        self.assertFalse((self.state/'receipt.json').exists())

    def test_symlink_and_missing_hook_block_install(self):
        self.config.unlink();outside=self.root/'outside';outside.write_bytes(self.original);self.config.symlink_to(outside)
        with self.assertRaises(ValueError):boot.prepare(self.root,'install','silhouette')
        self.config.unlink();self.config.write_bytes(self.original)
        (self.root/'etc/mkinitcpio.conf').write_text('HOOKS=(base systemd filesystems)\n')
        with self.assertRaises(ValueError):boot.prepare(self.root,'install','silhouette')
        self.assertEqual(self.config.read_bytes(),self.original)

    def test_preparation_does_not_write_system_state(self):
        files,_,_=boot.prepare(self.root,'install','silhouette')
        self.assertIn('assets/silhouette.png',files)
        self.assertFalse(self.destination.exists());self.assertFalse(self.state.exists())
        self.assertEqual(self.config.read_bytes(),self.original)

    @unittest.skipUnless(Path('/usr/lib/plymouth/script.so').is_file(),'Plymouth script parser unavailable')
    def test_native_plymouth_parser_accepts_silhouette(self):
        library=ctypes.CDLL('/usr/lib/plymouth/script.so')
        library.script_parse_string.argtypes=[ctypes.c_char_p,ctypes.c_char_p];library.script_parse_string.restype=ctypes.c_void_p
        library.script_parse_op_free.argtypes=[ctypes.c_void_p];library.script_parse_op_free.restype=None
        for mode in ['silhouette']:
            files,_,_=boot.prepare(self.root,'install',mode)
            op=library.script_parse_string(files['bankai.script'],b'bankai.script')
            self.assertTrue(op,mode);library.script_parse_op_free(op)


if __name__=='__main__':unittest.main()
