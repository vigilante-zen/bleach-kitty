"""Shared Bankai appearance preferences; no settings are written on import."""
import json
import os
from pathlib import Path
import random
import re
import tempfile

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

def load(home):
    path = Path(home) / '.local/share/bleach-desktop/appearance.json'
    checked(path, home)
    if not path.exists(): return defaults()
    return validate(json.loads(path.read_text()))

def save(home, value):
    value = validate(value)
    path = Path(home) / '.local/share/bleach-desktop/appearance.json'
    checked(path, home)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream: json.dump(value, stream, indent=2); stream.write('\n')
        os.replace(temp, path)
    finally: Path(temp).unlink(missing_ok=True)

def shuffled(home, current):
    settings = load(home)
    if not settings['shuffle_login']: return None
    pool = [p for p in settings['pool'] if p != current] or settings['pool']
    return random.SystemRandom().choice(pool)
