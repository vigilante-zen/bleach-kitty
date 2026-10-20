#!/usr/bin/env python3
"""Open an SDDM test preview of the selected desktop's manga scene."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from sync import read_preset

base = Path(__file__).resolve().parent
source = base / 'login-theme' if (base / 'login-theme').is_dir() else base / 'theme'
preset = read_preset(Path.home()) or 'ichigo'
with tempfile.TemporaryDirectory(prefix='bankai-login-preview-') as folder:
    theme = Path(folder)
    for name in ('Main.qml', 'metadata.desktop', 'theme.conf'):
        shutil.copyfile(source / name, theme / name)
    (theme / 'assets').symlink_to(source / 'assets', target_is_directory=True)
    (theme / 'theme.conf.user').write_text(f'[General]\nCharacter={preset}\n')
    subprocess.run(['sddm-greeter-qt6', '--test-mode', '--theme', str(theme)], check=True)
