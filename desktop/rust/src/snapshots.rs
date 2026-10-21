use std::{collections::BTreeSet, fs, os::unix::fs::{MetadataExt, PermissionsExt}, path::PathBuf};
use crate::{App, json::Value, obj, fsutil::{self, Result, TextResult, Lock}};
pub const BASELINE: &str = "20261019-202424-204727";

pub fn valid_name(name: &str) -> bool {
    name.len() == 22 && name.as_bytes().iter().enumerate().all(|(i,c)| if i == 8 || i == 15 { *c == b'-' } else { c.is_ascii_digit() })
}
fn catalog_strings(app: &App, key: &str) -> Result<Vec<String>> {
    app.catalog.get(key)?.array()?.iter().map(|v| Ok(v.text()?.to_string())).collect()
}
pub fn allowed(app: &App, relative: &str) -> bool {
    if !fsutil::valid_relative(relative) { return false; }
    let files = app.snapshot_paths.get("files").and_then(Value::array).map(|rows| rows.iter().filter_map(|v| v.text().ok()).collect::<Vec<_>>()).unwrap_or_default();
    let trees = app.snapshot_paths.get("trees").and_then(Value::array).map(|rows| rows.iter().filter_map(|v| v.text().ok()).collect::<Vec<_>>()).unwrap_or_default();
    if files.contains(&relative) || trees.iter().any(|t| relative.starts_with(&(t.to_string() + "/"))) { return true; }
    app.snapshot_paths.get("patterns").and_then(Value::array).is_ok_and(|patterns| patterns.iter().any(|pattern| {
        let directory = pattern.get("directory").and_then(Value::text).unwrap_or("");
        let prefix = pattern.get("prefix").and_then(Value::text).unwrap_or("");
        let suffix = pattern.get("suffix").and_then(Value::text).unwrap_or("");
        relative.strip_prefix(&(directory.to_string() + "/")).is_some_and(|name| {
            !name.contains('/') && name.starts_with(prefix) && name.ends_with(suffix)
        })
    }))
}

fn paths(app: &App) -> Result<BTreeSet<PathBuf>> {
    let mut files = BTreeSet::new();
    for tree in catalog_strings(app, "trees")? {
        let root = app.home.join(tree); fsutil::reject_links(&root, &app.home)?;
        files.extend(fsutil::walk(&root)?);
    }
    for relative in catalog_strings(app, "files")? {
        let path = app.home.join(relative); fsutil::reject_links(&path, &app.home)?;
        if path.is_file() { files.insert(path); }
    }
    for dir in [".config/fish/functions", ".config/fish/completions", ".local/share/color-schemes", ".local/share/applications"] {
        let root = app.home.join(dir); fsutil::reject_links(&root, &app.home)?;
        if !root.exists() { continue; }
        for item in fs::read_dir(root).text()? {
            let path = item.text()?.path();
            let relative = path.strip_prefix(&app.home).text()?.to_string_lossy();
            if allowed(app, &relative) { fsutil::reject_links(&path, &app.home)?; if path.is_file() { files.insert(path); } }
        }
    }
    Ok(files)
}
pub fn create(app: &App) -> Result<Value> {
    fsutil::reject_links(&app.snapshots, &app.home)?;
    fs::create_dir_all(&app.snapshots).text()?;
    let partial = app.snapshots.join(format!(".partial-rust-{}", fsutil::nonce()));
    fs::create_dir(&partial).text()?;
    let result = (|| {
        let mut entries = vec![];
        for path in paths(app)? {
            let relative = path.strip_prefix(&app.home).text()?.to_string_lossy().to_string();
            fsutil::reject_links(&path, &app.home)?;
            let dest = partial.join("files").join(&relative);
            fs::create_dir_all(dest.parent().unwrap()).text()?;
            fs::copy(&path, &dest).text()?;
            let mode = fs::metadata(&path).text()?.permissions().mode() & 0o777;
            fs::set_permissions(&dest, fs::Permissions::from_mode(mode)).text()?;
            entries.push(obj! { "path" => relative, "sha256" => fsutil::hash(&dest)?, "mode" => mode as u64 });
        }
        if entries.is_empty() { return Err("No theme files were found".into()); }
        let absent = catalog_strings(app, "files")?.into_iter().filter(|p| !app.home.join(p).exists()).map(Value::from).collect::<Vec<_>>();
        let manifest = obj! { "version" => 1u64, "files" => entries, "absent" => absent };
        let manifest_text = manifest.dump();
        if manifest_text.len() > fsutil::MAX_JSON_BYTES { return Err("Snapshot manifest exceeds the 16 MiB size limit".into()); }
        fsutil::atomic_write(&partial.join("manifest.json"), manifest_text.as_bytes(), Some(0o600))?;
        let name = fsutil::timestamp();
        let destination = app.snapshots.join(&name);
        if destination.exists() { return Err("Snapshot name collision; retry the operation".into()); }
        fs::rename(&partial, &destination).text()?;
        Ok(obj! { "name" => name, "files" => manifest.get("files")?.array()?.len(), "message" => "Snapshot saved." })
    })();
    if partial.exists() { let _ = fs::remove_dir_all(partial); }
    result
}

pub fn verify(app: &App, name: &str) -> Result<Value> {
    if !valid_name(name) { return Err("Invalid snapshot name".into()); }
    let root = app.snapshots.join(name); fsutil::reject_links(&root, &app.home)?;
    let path = root.join("manifest.json"); fsutil::reject_links(&path, &root)?;
    if !fs::symlink_metadata(&path).text()?.file_type().is_file() { return Err("Snapshot manifest is not a regular file".into()); }
    let manifest = fsutil::read_json(&path)?;
    if manifest.get("version")?.number()? != 1 { return Err("Unsupported snapshot version".into()); }
    let files = manifest.get("files")?.array()?;
    if files.is_empty() { return Err("Empty snapshot manifest".into()); }
    let mut seen = BTreeSet::new();
    for entry in files {
        let relative = entry.get("path")?.text()?;
        if !allowed(app, relative) || !seen.insert(relative.to_string()) { return Err(format!("Invalid snapshot path: {relative}")); }
        let mode = entry.get("mode")?.number()?;
        if mode > 0o777 { return Err("Invalid snapshot permissions".into()); }
        let source = root.join("files").join(relative); let dest = app.home.join(relative);
        fsutil::reject_links(&source, &root)?; fsutil::reject_links(&dest, &app.home)?;
        if !fs::symlink_metadata(&source).text()?.file_type().is_file() { return Err(format!("Snapshot payload is not a regular file: {relative}")); }
        if dest.exists() && !dest.is_file() { return Err(format!("Destination is not a file: {relative}")); }
        if fsutil::hash(&source)? != entry.get("sha256")?.text()? { return Err(format!("Integrity check failed: {relative}")); }
    }
    if let Some(absent) = manifest.opt("absent") {
        for entry in absent.array()? {
            let relative = entry.text()?;
            if !allowed(app, relative) || !seen.insert(relative.to_string()) { return Err("Invalid absent-file path".into()); }
            let path = app.home.join(relative); fsutil::reject_links(&path, &app.home)?;
            if path.exists() && !path.is_file() { return Err("Absent-file destination is not a file".into()); }
        }
    }
    Ok(manifest)
}
pub fn restore(app: &App, name: &str) -> Result<Value> {
    let manifest = verify(app, name)?;
    let mut edits = std::collections::BTreeMap::new();
    if let Some(absent) = manifest.opt("absent") {
        for relative in absent.array()? { edits.insert(relative.text()?.to_string(), None); }
    }
    for entry in manifest.get("files")?.array()? {
        let relative = entry.get("path")?.text()?.to_string();
        let source = app.snapshots.join(name).join("files").join(&relative);
        fsutil::reject_links(&source, &app.snapshots.join(name))?;
        let bytes = fs::read(source).text()?;
        if fsutil::hash_bytes(&bytes) != entry.get("sha256")?.text()? { return Err(format!("Integrity check failed: {relative}")); }
        edits.insert(relative, Some((bytes, entry.get("mode")?.number()? as u32)));
    }
    let previous = create(app)?;
    restore_transaction_with(app, &edits, |path, bytes, mode| fsutil::atomic_write(path, bytes, Some(mode)))?;
    Ok(obj! { "message" => "Snapshot restored. Log out and back in to reload KDE.", "previous" => previous.get("name")?.clone() })
}

pub(crate) fn restore_transaction_with<F>(app: &App, edits: &std::collections::BTreeMap<String,Option<(Vec<u8>,u32)>>, mut writer: F) -> Result<()>
where F: FnMut(&std::path::Path, &[u8], u32) -> Result<()> {
    let mut originals = std::collections::BTreeMap::<String,Option<(Vec<u8>,u32)>>::new();
    for (relative, replacement) in edits {
        if !allowed(app, relative) { return Err(format!("Invalid snapshot path: {relative}")); }
        if replacement.as_ref().is_some_and(|(_, mode)| *mode > 0o777) { return Err("Invalid snapshot permissions".into()); }
        let path = app.home.join(relative);
        fsutil::reject_links(&path, &app.home)?;
        let original = match fs::symlink_metadata(&path) {
            Ok(metadata) if metadata.is_file() => Some((fs::read(&path).text()?, metadata.permissions().mode() & 0o777)),
            Ok(_) => return Err(format!("Destination is not a file: {relative}")),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => None,
            Err(error) => return Err(error.to_string()),
        };
        originals.insert(relative.clone(), original);
    }

    let mut attempted = Vec::new();
    for (relative, replacement) in edits {
        let path = app.home.join(relative);
        attempted.push(relative.clone());
        let result = (|| {
            fsutil::reject_links(&path, &app.home)?;
            match replacement {
                Some((bytes, mode)) => writer(&path, bytes, *mode),
                None => fsutil::remove_if_exists(&path),
            }
        })();
        if let Err(error) = result {
            let mut rollback_errors = Vec::new();
            for previous in attempted.iter().rev() {
                let path = app.home.join(previous);
                let rollback = (|| {
                    fsutil::reject_links(&path, &app.home)?;
                    match originals.get(previous).and_then(Option::as_ref) {
                        Some((bytes, mode)) => fsutil::atomic_write(&path, bytes, Some(*mode)),
                        None => fsutil::remove_if_exists(&path),
                    }
                })();
                if let Err(rollback_error) = rollback { rollback_errors.push(format!("{}: {rollback_error}", path.display())); }
            }
            let message = format!("Could not restore {relative}: {error}");
            return if rollback_errors.is_empty() { Err(message) }
                else { Err(format!("{message}; rollback also failed for {}", rollback_errors.join(", "))) };
        }
    }
    Ok(())
}

fn protections(app: &App) -> Result<BTreeSet<String>> {
    let path = app.state.join("protected-snapshots.json"); fsutil::reject_links(&path, &app.home)?;
    if !path.exists() { return Ok(BTreeSet::new()); }
    if !path.is_file() { return Err("Protection metadata is not a regular file; cleanup is disabled".into()); }
    fsutil::read_json(&path)?.array()?.iter().map(|v| {
        let name = v.text()?; if !valid_name(name) { return Err("Invalid protection metadata; cleanup is disabled".into()); }
        Ok(name.to_string())
    }).collect()
}
pub fn protect(app: &App, name: &str, enabled: bool) -> Result<Value> {
    if !valid_name(name) { return Err("Invalid snapshot name".into()); }
    let path = app.snapshots.join(name); fsutil::reject_links(&path, &app.home)?;
    let manifest = path.join("manifest.json"); fsutil::reject_links(&manifest, &path)?;
    if !manifest.is_file() { return Err("Snapshot was not found".into()); }
    if name == BASELINE && !enabled { return Err("The original restore baseline stays protected".into()); }
    let mut names = protections(app)?;
    if enabled { names.insert(name.to_string()); } else { names.remove(name); }
    let value = Value::from(names.into_iter().map(Value::from).collect::<Vec<_>>());
    fsutil::atomic_write(&app.state.join("protected-snapshots.json"), value.dump().as_bytes(), Some(0o600))?;
    Ok(obj! { "message" => if enabled { "Snapshot protected from cleanup." } else { "Snapshot protection removed." } })
}

pub fn scan(app: &App) -> Result<Vec<Value>> {
    fsutil::reject_links(&app.snapshots, &app.home)?;
    let protected = protections(app)?;
    if !app.snapshots.exists() { return Ok(vec![]); }
    let mut dirs = fs::read_dir(&app.snapshots).text()?.collect::<std::io::Result<Vec<_>>>().text()?;
    dirs.sort_by_key(|d| std::cmp::Reverse(d.file_name()));
    let mut rows = vec![];
    for dir in dirs {
        let name = dir.file_name().to_string_lossy().to_string();
        let path = dir.path();
        if name.starts_with('.') || !dir.file_type().text()?.is_dir() || !path.join("manifest.json").is_file() { continue; }
        let mut size = 0u64; let mut count = 0usize;
        let inspected = (|| -> Result<String> {
            if !valid_name(&name) { return Err("Unrecognized snapshot name".into()); }
            fsutil::reject_links(&path.join("manifest.json"), &path)?;
            let manifest = fsutil::read_json(&path.join("manifest.json"))?;
            if manifest.get("version")?.number()? != 1 { return Err("Invalid snapshot version".into()); }
            let mut expected = BTreeSet::from(["manifest.json".to_string()]);
            let mut seen = BTreeSet::new();
            count = manifest.get("files")?.array()?.len();
            if count == 0 { return Err("Empty snapshot".into()); }
            for entry in manifest.get("files")?.array()? {
                let relative = entry.get("path")?.text()?;
                if !allowed(app, relative) || !seen.insert(relative.to_string()) { return Err("Invalid or duplicate snapshot path".into()); }
                expected.insert(format!("files/{relative}"));
            }
            if let Some(absent) = manifest.opt("absent") {
                for entry in absent.array()? {
                    let relative = entry.text()?;
                    if !allowed(app, relative) || !seen.insert(relative.to_string()) { return Err("Invalid or duplicate absent-file path".into()); }
                }
            }
            let mut actual = BTreeSet::new(); let mut stamps = vec![];
            for file in fsutil::walk(&path)? {
                let meta = fs::metadata(&file).text()?;
                size = size.checked_add(meta.len()).ok_or("Snapshot size overflow")?;
                let relative = file.strip_prefix(&path).text()?.to_string_lossy().to_string(); actual.insert(relative.clone());
                stamps.push(format!("{relative}:{}:{}:{}:{}:{}",meta.dev(),meta.ino(),meta.len(),meta.mtime(),meta.mtime_nsec()));
            }
            if actual != expected { return Err("Missing or additional files; review manually".into()); }
            let meta = fs::metadata(&path).text()?;
            Ok(format!("{}:{}:{}:{}:{}:{}",meta.dev(),meta.ino(),meta.mtime(),meta.mtime_nsec(),fsutil::hash(&path.join("manifest.json"))?,fsutil::hash_bytes(stamps.join("|").as_bytes())))
        })();
        let eligible = inspected.is_ok(); let reason = inspected.as_ref().err().cloned().unwrap_or_default();
        rows.push(obj! { "name" => name.clone(), "bytes" => size, "files" => count,
            "protected" => protected.contains(&name) || name == BASELINE, "baseline" => name == BASELINE,
            "eligible" => eligible, "reason" => reason, "fingerprint" => inspected.unwrap_or_default() });
    }
    Ok(rows)
}
pub fn plan(app: &App, keep: usize) -> Result<Value> {
    if keep == 0 || keep > 1000 { return Err("Keep between 1 and 1000 snapshots".into()); }
    let rows = scan(app)?;
    let mut remaining = keep; let mut candidates = vec![]; let mut bytes = 0u64;
    for row in rows {
        if !row.get("eligible")?.boolean()? { continue; }
        if remaining > 0 { remaining -= 1; continue; }
        if !row.get("protected")?.boolean()? { bytes += row.get("bytes")?.number()?; candidates.push(row); }
    }
    Ok(obj! { "version" => 1u64, "keep" => keep, "candidates" => candidates, "bytes" => bytes })
}
pub fn cleanup(app: &App, reviewed: &Value) -> Result<Value> {
    if reviewed.get("version")?.number()? != 1 { return Err("Invalid cleanup plan".into()); }
    let current = plan(app, usize::try_from(reviewed.get("keep")?.number()?).text()?)?;
    let targets = reviewed.get("candidates")?.array()?; let mut seen = BTreeSet::new(); let mut bytes = 0;
    for target in targets {
        let name = target.get("name")?.text()?;
        if !valid_name(name) || !seen.insert(name) { return Err("Invalid cleanup target".into()); }
        let found = current.get("candidates")?.array()?.iter().find(|row| row.get("name").and_then(Value::text).ok() == Some(name)).ok_or("Snapshots or protections changed. Preview cleanup again.")?;
        if found.get("fingerprint")? != target.get("fingerprint")? { return Err("A snapshot changed. Preview cleanup again.".into()); }
        bytes += found.get("bytes")?.number()?;
    }
    for name in seen { fs::remove_dir_all(app.snapshots.join(name)).text()?; }
    Ok(obj! { "message" => format!("Removed {} reviewed snapshots.", targets.len()), "bytes" => bytes })
}

pub fn locked_dispatch(app: &App, op: &str, request: &Value) -> Result<Value> {
    fsutil::reject_links(&app.state, &app.home)?;
    let _lock = Lock::acquire(&app.state)?;
    match op {
        "backup" => create(app),
        "verify" => { let manifest = verify(app, request.get("name")?.text()?)?; Ok(obj! { "message" => format!("Verified {} snapshot files.", manifest.get("files")?.array()?.len()) }) },
        "restore" => restore(app, request.get("name")?.text()?),
        "protect" => protect(app, request.get("name")?.text()?, request.get("enabled")?.boolean()?),
        "cleanup" => cleanup(app, request.get("plan")?),
        _ => Err("Unknown snapshot operation".into()),
    }
}
