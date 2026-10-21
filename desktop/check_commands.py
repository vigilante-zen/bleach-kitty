#!/usr/bin/env python3
"""Check shared Bankai command routing across edition installs and removals."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(edition, home, action=None, binary=None):
    command = ['python3', str(ROOT / 'desktop' / edition / 'install.py')]
    if action is not None:
        command.append(action)
    command += ['--home', str(home), '--skip-theme']
    if binary is not None:
        command += ['--binary', str(binary)]
    subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


def output(command, home):
    env = dict(os.environ, HOME=str(home))
    return subprocess.run([str(home / '.local/bin' / command), '--help'], cwd=ROOT,
                          env=env, check=True, capture_output=True, text=True).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rust-binary', type=Path, required=True)
    binary = parser.parse_args().rust_binary.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='bankai-command-check-') as temp:
        home = Path(temp) / 'python-first'
        run('python', home)
        python_desktop = home / '.local/share/applications/bleach-bankai.desktop'
        assert '/.local/bin/bankai-python"' in python_desktop.read_text()
        assert 'Open the Bankai control center' in output('bankai', home)
        assert 'Open the Bankai control center' in output('bankai-python', home)

        run('rust', home, binary=binary)
        assert '/.local/bin/bankai-python"' in python_desktop.read_text()
        rust_help = output('bankai', home)
        assert 'The Python edition is bankai-python.' in rust_help
        assert 'The Python edition is bankai-python.' in output('bankai-rust', home)
        assert 'Open the Bankai control center' in output('bankai-python', home)

        run('rust', home, binary=binary)  # idempotent shared ownership
        run('rust', home, action='uninstall')
        assert 'Open the Bankai control center' in output('bankai', home)
        run('python', home, action='uninstall')
        assert not (home / '.local/bin/bankai').exists()

        home = Path(temp) / 'rust-first'
        run('rust', home, binary=binary)
        run('python', home)
        assert '/.local/bin/bankai-python"' in (home / '.local/share/applications/bleach-bankai.desktop').read_text()
        assert 'The Python edition is bankai-python.' in output('bankai', home)
        run('python', home, action='uninstall')
        assert 'The Python edition is bankai-python.' in output('bankai', home)
        run('rust', home, action='uninstall')
        assert not (home / '.local/bin/bankai').exists()
    print('Verified Bankai command routing, edition switching and shared uninstall ownership.')


if __name__ == '__main__':
    main()
