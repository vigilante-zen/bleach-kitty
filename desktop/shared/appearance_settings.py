"""Shared Bankai appearance preferences; no settings are written on import."""
import fcntl
from contextlib import contextmanager
import json
import os
from pathlib import Path
import random
import re
import stat
import tempfile
import uuid

MAX_CUSTOM_PRESET_BYTES = 64 * 1024

def _read_custom_presets(path):
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return []
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError('Saved custom presets must be stored in a regular file')
    with path.open('rb') as stream:
        data = stream.read(MAX_CUSTOM_PRESET_BYTES + 1)
    if len(data) > MAX_CUSTOM_PRESET_BYTES:
        raise ValueError('Saved custom presets exceed the 64 KiB size limit')
    return json.loads(data.decode('utf-8'))

def _write_custom_presets(path, rows, home):
    data = (json.dumps(rows, indent=2) + '\n').encode('utf-8')
    if len(data) > MAX_CUSTOM_PRESET_BYTES:
        raise ValueError('Saved custom presets exceed the 64 KiB size limit')
    checked(path, home)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)

def catalog():
    return json.loads((Path(__file__).resolve().parent / 'presets.json').read_text())['presets']

def defaults():
    return dict(edition='color', accent='', login='follow', shuffle_login=False, pool=[p['id'] for p in catalog()])

def validate(value):
    keys = {p['id'] for p in catalog()}
    if not isinstance(value, dict): raise ValueError('Invalid appearance preferences')
    if value.get('edition') not in ('color', 'manga'): raise ValueError('Choose color or manga backgrounds')
    if not isinstance(value.get('accent'), str) or (value['accent'] and not re.fullmatch(r'#[0-9a-fA-F]{6}', value['accent'])):
        raise ValueError('Accent must be empty or a six-digit hex color, such as #a9dfff')
    if not isinstance(value.get('login'), str) or value['login'] not in keys | {'follow'}: raise ValueError('Choose a login character or follow background')
    if type(value.get('shuffle_login')) is not bool: raise ValueError('Invalid login shuffle option')
    pool = value.get('pool')
    if not isinstance(pool, list) or not pool or any(not isinstance(k, str) or k not in keys for k in pool) or len(set(pool)) != len(pool):
        raise ValueError('Choose at least one unique character for the shuffle pool')
    return {key: value[key] for key in defaults()}

def checked(path, home):
    for part in (path, *path.parents):
        if part.is_symlink(): raise ValueError('Linked appearance preferences are unsupported')
        if part == Path(home): break

@contextmanager
def shared_state_lock(home):
    """Coordinate read-modify-write operations with Rust and snapshot tools."""
    state = Path(home) / '.local/state/bleach-desktop'
    checked(state, home)
    state.mkdir(parents=True, exist_ok=True)
    lock_path = state / 'snapshot-management.lock'
    checked(lock_path, home)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)

def load(home):
    path = Path(home) / '.local/share/bleach-desktop/appearance.json'
    checked(path, home)
    if not path.exists(): return defaults()
    return validate(json.loads(path.read_text()))

def write_preferences(path, value):
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream: json.dump(value, stream, indent=2); stream.write('\n')
        os.replace(temp, path)
    finally: Path(temp).unlink(missing_ok=True)

def save(home, value, expected=None):
    value = validate(value)
    path = Path(home) / '.local/share/bleach-desktop/appearance.json'
    checked(path, home)
    path.parent.mkdir(parents=True, exist_ok=True)
    with shared_state_lock(home):
        if expected is not None and load(home) != validate(expected):
            raise ValueError('Appearance settings changed in another Bankai window. Close and reopen Appearance options before saving.')
        write_preferences(path, value)

def repair(home):
    path = Path(home) / '.local/share/bleach-desktop/appearance.json'
    checked(path, home)
    with shared_state_lock(home):
        checked(path, home)
        try: load(home)
        except (OSError, ValueError, TypeError): pass
        else: raise ValueError('Appearance settings are readable again. Reopen Appearance options.')
        replacement = defaults()
        backup = None
        if path.exists():
            backup = path.with_name(path.name + '.corrupt-' + uuid.uuid4().hex)
            os.replace(path, backup)
        try:
            write_preferences(path, replacement)
        except OSError as error:
            if backup is not None:
                try: os.replace(backup, path)
                except OSError as restore_error:
                    raise OSError(f'{error}; could not restore the unreadable settings file: {restore_error}') from error
            raise
        message = 'Appearance settings were restored to defaults.'
        if backup is not None: message += ' The unreadable file was preserved as ' + str(backup) + '.'
        return dict(message=message, backup=str(backup) if backup is not None else '')

def shuffled(home, current):
    settings = load(home)
    if not settings['shuffle_login']: return None
    pool = [p for p in settings['pool'] if p != current] or settings['pool']
    return random.SystemRandom().choice(pool)

def custom_presets(home):
    path = Path(home) / '.local/share/bleach-desktop/custom-presets.json'
    checked(path, home)
    value = _read_custom_presets(path)
    if not isinstance(value, list) or len(value) > 50: raise ValueError('Invalid saved preset list')
    keys = {p['id'] for p in catalog()}
    names = set(); ids = set(); result = []
    for row in value:
        if not isinstance(row, dict): raise ValueError('Invalid saved preset')
        name, preset, accent, login, edition, identifier = (row.get(k) for k in ('name','preset','accent','login','edition','id'))
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 40: raise ValueError('Saved preset names must be 1–40 characters')
        if not isinstance(identifier, str) or not identifier.startswith('custom-') or len(identifier) > 64: raise ValueError('Invalid saved preset id')
        if identifier in ids or name.casefold() in names: raise ValueError('Saved preset names and ids must be unique')
        if preset not in keys or login not in keys | {'follow'}: raise ValueError('Saved preset references an unknown character')
        if edition not in ('color','manga'): raise ValueError('Saved preset has an invalid wallpaper edition')
        if not isinstance(accent,str) or (accent and not re.fullmatch(r'#[0-9a-fA-F]{6}',accent)): raise ValueError('Saved preset has an invalid accent color')
        ids.add(identifier); names.add(name.casefold()); result.append(dict(id=identifier,name=name.strip(),preset=preset,accent=accent,login=login,edition=edition))
    return result

def save_custom_preset(home, name, preset, options):
    name = name.strip()
    if not name or len(name) > 40: raise ValueError('Name the preset with 1–40 characters')
    if preset not in {p['id'] for p in catalog()}: raise ValueError('Choose a Bankai character or form first')
    value = validate(options)
    path = Path(home) / '.local/share/bleach-desktop/custom-presets.json'
    with shared_state_lock(home):
        rows = custom_presets(home)
        if any(row['name'].casefold() == name.casefold() for row in rows): raise ValueError('A saved preset already has that name')
        if len(rows) >= 50: raise ValueError('You can save up to 50 custom presets')
        row = dict(id='custom-' + uuid.uuid4().hex, name=name, preset=preset, accent=value['accent'], login=value['login'], edition=value['edition'])
        rows.append(row)
        _write_custom_presets(path, rows, home)
        return row

def delete_custom_preset(home, identifier):
    path = Path(home) / '.local/share/bleach-desktop/custom-presets.json'
    with shared_state_lock(home):
        rows = custom_presets(home)
        kept = [row for row in rows if row['id'] != identifier]
        if len(kept) == len(rows): raise ValueError('Saved preset not found')
        _write_custom_presets(path, kept, home)
