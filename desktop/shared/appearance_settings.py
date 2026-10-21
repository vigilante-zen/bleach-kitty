"""Shared Bankai appearance preferences; no settings are written on import."""
import json
import os
from pathlib import Path
import random
import re
import tempfile
import uuid

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

def custom_presets(home):
    path = Path(home) / '.local/share/bleach-desktop/custom-presets.json'
    checked(path, home)
    if not path.exists(): return []
    value = json.loads(path.read_text())
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
    rows = custom_presets(home)
    if any(row['name'].casefold() == name.casefold() for row in rows): raise ValueError('A saved preset already has that name')
    if len(rows) >= 50: raise ValueError('You can save up to 50 custom presets')
    value = validate(options)
    rows.append(dict(id='custom-' + uuid.uuid4().hex, name=name, preset=preset, accent=value['accent'], login=value['login'], edition=value['edition']))
    path = Path(home) / '.local/share/bleach-desktop/custom-presets.json'
    checked(path, home); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream: json.dump(rows,stream,indent=2); stream.write('\n')
        os.replace(temp,path)
    finally: Path(temp).unlink(missing_ok=True)
    return rows[-1]

def delete_custom_preset(home, identifier):
    rows = custom_presets(home)
    kept = [row for row in rows if row['id'] != identifier]
    if len(kept) == len(rows): raise ValueError('Saved preset not found')
    path = Path(home) / '.local/share/bleach-desktop/custom-presets.json'
    checked(path,home)
    fd,temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream: json.dump(kept,stream,indent=2); stream.write('\n')
        os.replace(temp,path)
    finally: Path(temp).unlink(missing_ok=True)
