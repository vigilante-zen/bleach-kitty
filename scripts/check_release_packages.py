#!/usr/bin/env python3
"""Verify checksums, edition separation, extracted installers and snapshot restore."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


def check_snapshot_restore(root, edition, temporary):
    python_command = [str(root / 'desktop/python/bin/bankai-desktop-backup')]
    binary = root / 'desktop/rust/bin/bankai-rust'
    if edition == 'python':
        command = python_command
    elif binary.is_file():
        command = [str(binary)]
    else:
        return

    home = temporary / (edition + '-restore-home')
    kitty = home / '.config/kitty/kitty.conf'
    kitty.parent.mkdir(parents=True)
    kitty.write_text('font_size 12\n')
    globals_ = home / '.config/kdeglobals'
    globals_.parent.mkdir(parents=True, exist_ok=True)
    globals_.write_text('[General]\nColorScheme=BleachRukia\n')
    env = dict(os.environ, HOME=str(home))
    if edition == 'rust':
        env['BANKAI_HOME'] = str(home)
    create = command if edition == 'python' else command + ['backup']
    subprocess.run(create, cwd=root, env=env, check=True, capture_output=True, text=True)
    snapshot_root = home / 'Backups/Bleach-Desktop'
    snapshots = sorted(path for path in snapshot_root.iterdir() if path.is_dir() and (path / 'manifest.json').is_file())
    if len(snapshots) != 1:
        raise ValueError(f'{edition} packaged backup did not create exactly one snapshot')

    name = snapshots[0].name
    kitty.write_text('font_size 24\n')
    globals_.write_text('[General]\nColorScheme=BreezeDark\n')
    absent = home / '.config/fish/config.fish'
    absent.parent.mkdir(parents=True)
    absent.write_text('# added after snapshot\n')
    restore = command + ['restore', name]
    subprocess.run(restore, cwd=root, env=env, check=True, capture_output=True, text=True)
    if kitty.read_text() != 'font_size 12\n' or globals_.read_text() != '[General]\nColorScheme=BleachRukia\n' or absent.exists():
        raise ValueError(f'{edition} packaged snapshot restore did not restore files and absences')
    if len([path for path in snapshot_root.iterdir() if path.is_dir() and (path / 'manifest.json').is_file()]) != 2:
        raise ValueError(f'{edition} packaged restore did not preserve a pre-restore snapshot')


def check_installed_python_snapshot_policy(package_root, home):
    subprocess.run(['python3', str(package_root / 'desktop/python/install.py'), '--home', str(home), '--skip-theme'],
                   cwd=package_root, check=True, capture_output=True, text=True)
    data = home / '.local/share/bleach-desktop'
    manager = data / 'snapshot_manager.py'
    if not manager.is_file() or not (data / 'snapshot_paths.json').is_file():
        raise ValueError('Python install is missing its shared snapshot policy.')
    spec = importlib.util.spec_from_file_location('installed_bankai_snapshot_manager', manager)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    snapshots = home / 'Backups/Bleach-Desktop'
    allowed_path = '.local/share/plasma/look-and-feel/org.zen.bleach.desktop/metadata.json'
    rejected_path = '.ssh/id_rsa'
    for name, relative in [('20261020-120000-000000', allowed_path),
                           ('20261020-120001-000000', rejected_path)]:
        directory = snapshots / name
        payload = directory / 'files' / relative
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_text('snapshot payload\n')
        (directory / 'manifest.json').write_text(json.dumps({'version': 1, 'files': [{'path': relative}]}))
    store = module.SnapshotStore(snapshots, home / '.local/state/bleach-desktop')
    rows = {row['name']: row for row in store.scan()}
    if not rows['20261020-120000-000000']['eligible'] or rows['20261020-120001-000000']['eligible']:
        raise ValueError('Installed Python scanner does not enforce the shared snapshot policy.')


def check(archive):
    with archive.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    if archive.with_suffix(archive.suffix + '.sha256').read_text().split()[0] != checksum:
        raise ValueError(f'Checksum mismatch: {archive}')
    with tempfile.TemporaryDirectory(prefix='bankai-release-verify-') as temp:
        unpack = Path(temp) / 'package'; unpack.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(unpack, filter='data')
        roots = list(unpack.iterdir())
        if len(roots) != 1 or not roots[0].is_dir():
            raise ValueError('Expected a single package root')
        root = roots[0]
        metadata = json.loads((root / 'PACKAGE.json').read_text())
        edition = metadata['edition']
        if edition not in ['python', 'rust']:
            raise ValueError('Unknown package edition')
        other = 'rust' if edition == 'python' else 'python'
        if (root / 'desktop' / other).exists():
            raise ValueError('Package includes the other desktop edition')
        binary = root / 'desktop/rust/bin/bankai-rust'
        if metadata['prebuilt'] != binary.is_file():
            raise ValueError('Prebuilt metadata does not match package contents')
        home = Path(temp) / 'staging-home'
        subprocess.run(['python3', str(root / f'desktop/{edition}/install.py'),
                        '--dry-run', '--home', str(home)], cwd=root, check=True)
        if home.exists():
            raise ValueError('Dry run wrote to the staging home')
        if edition == 'python':
            check_installed_python_snapshot_policy(root, home)
        check_snapshot_restore(root, edition, Path(temp))
        login = root / 'login/install.py'
        required = ['login/README.md', 'login/ARTWORK.json', 'login/sync.py', 'login/greeter_preview.py', 'login/legacy-theme.json', 'login/theme/Main.qml', 'login/theme/metadata.desktop',
                    'login/theme/theme.conf', 'login/theme/assets/ichigo.png']
        if not login.is_file() or any(not (root / name).is_file() for name in required):
            raise ValueError('Package is missing the optional login theme')
        system = Path(temp) / 'staging-system'
        command = ['python3', str(login), '--root', str(system)]
        subprocess.run(command + ['--dry-run'], check=True)
        if system.exists():
            raise ValueError('Login dry run wrote to the staging system')
        subprocess.run(command, check=True)
        subprocess.run(command + ['restore'], check=True)
        if (system / 'etc/sddm.conf.d/zz-bankai-manga.conf').exists():
            raise ValueError('Login restore left the active theme override')

    print('Verified:', archive.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=Path('dist'))
    args = parser.parse_args()
    archives = sorted(args.directory.glob('*.tar.gz'))
    if not archives:
        parser.error('No release archives found')
    for archive in archives:
        check(archive.resolve())


if __name__ == '__main__':
    main()
