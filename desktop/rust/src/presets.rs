use std::{collections::BTreeMap, fs, path::Path, process::{Command, Stdio}, io::Read, thread, time::{Duration, Instant}};
use crate::{App, json::{self, Value}, obj, fsutil::{self, Result, TextResult, Lock}, snapshots};

pub fn put(text: &str, section: &str, key: &str, value: &str) -> String {
    let mut lines: Vec<String> = text.lines().map(str::to_string).collect();
    let header = format!("[{section}]");
    if let Some(begin) = lines.iter().position(|line| line == &header) {
        let end = (begin + 1..lines.len()).find(|i| lines[*i].starts_with('[')).unwrap_or(lines.len());
        if let Some(index) = (begin + 1..end).find(|i| lines[*i].starts_with(&format!("{key}="))) { lines[index] = format!("{key}={value}"); }
        else { lines.insert(end, format!("{key}={value}")); }
    } else { lines.extend([String::new(), header, format!("{key}={value}")]); }
    lines.join("\n") + "\n"
}
pub fn uri(path: &Path) -> String {
    use std::os::unix::ffi::OsStrExt;
    let mut out = String::from("file://");
    for byte in path.as_os_str().as_bytes() {
        if byte.is_ascii_alphanumeric() || b"/-._~".contains(byte) { out.push(*byte as char); }
        else { out.push_str(&format!("%{byte:02X}")); }
    }
    out
}
pub fn run(program: &str, args: &[&str]) -> Result<(bool, String)> {
    let mut child = Command::new(program).args(args).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().text()?;
    let out = child.stdout.take().unwrap(); let err = child.stderr.take().unwrap();
    let reader = |stream: Box<dyn Read + Send>| thread::spawn(move || { let mut bytes = vec![]; let _ = stream.take(1_048_576).read_to_end(&mut bytes); bytes });
    let stdout = reader(Box::new(out)); let stderr = reader(Box::new(err));
    let started = Instant::now();
    let status = loop {
        if let Some(status) = child.try_wait().text()? { break status; }
        if started.elapsed() > Duration::from_secs(20) { let _ = child.kill(); let _ = child.wait(); return Err(format!("{program} timed out")); }
        thread::sleep(Duration::from_millis(15));
    };
    let mut text = String::from_utf8_lossy(&stdout.join().unwrap_or_default()).to_string();
    text.push_str(&String::from_utf8_lossy(&stderr.join().unwrap_or_default()));
    Ok((status.success(), text))
}

fn write_transaction(app: &App, edits: &BTreeMap<String,String>) -> Result<()> {
    write_transaction_with(app, edits, |path, bytes| fsutil::atomic_write(path, bytes, None))
}

pub(crate) fn write_transaction_with<F>(app: &App, edits: &BTreeMap<String,String>, mut writer: F) -> Result<()>
where F: FnMut(&Path, &[u8]) -> Result<()> {
    let mut originals = BTreeMap::<String,Option<Vec<u8>>>::new();
    for relative in edits.keys() {
        if !fsutil::valid_relative(relative) { return Err(format!("Invalid configuration path: {relative}")); }
        let path = app.home.join(relative);
        fsutil::reject_links(&path, &app.home)?;
        let original = match fs::symlink_metadata(&path) {
            Ok(metadata) if metadata.is_file() => Some(fs::read(&path).text()?),
            Ok(_) => return Err(format!("Refusing to replace a non-file configuration path: {relative}")),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => None,
            Err(error) => return Err(error.to_string()),
        };
        originals.insert(relative.clone(), original);
    }

    let mut attempted = Vec::new();
    for (relative, text) in edits {
        let path = app.home.join(relative);
        attempted.push(relative.clone());
        if let Err(error) = writer(&path, text.as_bytes()) {
            let mut rollback_errors = Vec::new();
            for previous in attempted.iter().rev() {
                let path = app.home.join(previous);
                let rollback = match originals.get(previous).and_then(Option::as_deref) {
                    Some(bytes) => fsutil::atomic_write(&path, bytes, None),
                    None => fsutil::remove_if_exists(&path),
                };
                if let Err(rollback_error) = rollback {
                    rollback_errors.push(format!("{}: {rollback_error}", path.display()));
                }
            }
            let message = format!("Could not update {relative}: {error}");
            return if rollback_errors.is_empty() { Err(message) }
                else { Err(format!("{message}; rollback also failed for {}", rollback_errors.join(", "))) };
        }
    }
    Ok(())
}

pub fn apply(app: &App, name: &str) -> Result<Value> {
    apply_with_expected_appearance(app, name, None)
}

pub fn apply_with_expected_appearance(app: &App, name: &str, expected: Option<&Value>) -> Result<Value> {
    apply_with_appearance_changes(app, name, expected, None)
}

pub fn apply_with_appearance_changes(app: &App, name: &str, expected: Option<&Value>, replacement: Option<&Value>) -> Result<Value> {
    let preset = app.preset(name)?;
    let _lock = Lock::acquire(&app.state)?;
    let current_appearance = crate::appearance::load(app)?;
    if let Some(expected) = expected
        && current_appearance != crate::appearance::validate(app, expected)? {
        return Err("Appearance settings changed while applying the saved preset. Retry the action.".into());
    }
    let appearance = match replacement {
        Some(value) => crate::appearance::validate(app, value)?,
        None => current_appearance,
    };
    let image = app.wallpapers.join(preset.get(if appearance.get("edition")?.text()? == "manga" { "manga" } else { "image" })?.text()?);
    let scheme = format!("Bleach{}", preset.get("title")?.text()?);
    let scheme_file = app.home.join(".local/share/color-schemes").join(format!("{scheme}.colors"));
    for path in [&image, &scheme_file] {
        fsutil::reject_links(path, &app.home)?;
        if !path.is_file() { return Err(format!("Required asset is missing: {}", path.display())); }
    }
    let source = fs::read_to_string(&scheme_file).text()?;
    let mut edits: BTreeMap<String,String> = BTreeMap::new();
    let mut edit = |relative: &str, section: &str, key: &str, value: &str| -> Result<()> {
        let path = app.home.join(relative); fsutil::reject_links(&path, &app.home)?;
        let text = if let Some(text) = edits.get(relative) { text.clone() } else if path.exists() { fs::read_to_string(&path).text()? } else { String::new() };
        edits.insert(relative.into(), put(&text, section, key, value)); Ok(())
    };
    let mut section = "";
    for line in source.lines() {
        if line.starts_with('[') && line.ends_with(']') { section = &line[1..line.len()-1]; }
        else if (section.starts_with("Colors:") || section == "WM") && let Some((key,value)) = line.split_once('=') {
            edit(".config/kdeglobals", section, key, value)?;
        }
    }
    let custom = appearance.get("accent")?.text()?;
    let accent = if custom.is_empty() { preset.get("accent")?.text()? } else { custom };
    let rgb = [1,3,5].iter().map(|i| u8::from_str_radix(&accent[*i..*i+2],16).map(|n|n.to_string())).collect::<std::result::Result<Vec<_>,_>>().text()?.join(",");
    edit(".config/kdeglobals", "General", "ColorScheme", &scheme)?;
    edit(".config/kdeglobals", "General", "AccentColor", &rgb)?;
    edit(".config/plasmarc", "Theme", "name", "breeze-dark")?;
    edit(".config/kscreenlockerrc", "Greeter", "WallpaperPlugin", "org.kde.image")?;
    edit(".config/kscreenlockerrc", "Greeter][Wallpaper][org.kde.image][General", "Image", &uri(&image))?;
    edit(".config/kscreenlockerrc", "Greeter][Wallpaper][org.kde.image][General", "FillMode", "2")?;
    let applet_path = app.home.join(".config/plasma-org.kde.plasma.desktop-appletsrc");
    fsutil::reject_links(&applet_path, &app.home)?;
    let applets = fs::read_to_string(&applet_path).text()?;
    let mut current = String::new(); let mut desktop_groups = vec![];
    for line in applets.lines() {
        if line.starts_with('[') { current = line.to_string(); }
        else if matches!(line, "plugin=org.kde.plasma.folder" | "plugin=org.kde.plasma.desktop") && current.starts_with("[Containments][") && current.matches('[').count() == 2 {
            desktop_groups.push(current.trim_start_matches('[').trim_end_matches(']').to_string());
        }
    }
    for group in desktop_groups { edit(".config/plasma-org.kde.plasma.desktop-appletsrc", &(group + "][Wallpaper][org.kde.image][General"), "Image", &uri(&image))?; }
    drop(edit);
    let kitty_path = app.home.join(".config/kitty/kitty.conf"); fsutil::reject_links(&kitty_path, &app.home)?;
    let kitty = fs::read_to_string(&kitty_path).text()?;
    let include = "include themes/bleach-desktop.conf";
    if !kitty.lines().any(|line| line == include) { edits.insert(".config/kitty/kitty.conf".into(), format!("{}\n\n{include}\n",kitty.trim_end())); }
    edits.insert(".config/kitty/themes/bleach-desktop.conf".into(), format!("# Managed by Bankai Rust\ncursor {accent}\nactive_border_color {accent}\nactive_tab_background {accent}\nactive_tab_foreground #090c12\nselection_background {accent}\nselection_foreground #090c12\ncolor1 {accent}\ncolor9 {accent}\n"));
    let follow_path = app.home.join(".config/fastfetch/portrait-follow-desktop");
    fsutil::reject_links(&follow_path, &app.home)?;
    let follow = match fs::read_to_string(&follow_path) {
        Ok(value) => value.trim() == "on",
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => false,
        Err(e) => return Err(e.to_string()),
    };
    if follow {
        edits.insert(".config/fastfetch/portrait-choice".into(), format!("{}\n", preset.get("portrait")?.text()?));
    }
    edits.insert(".local/share/bleach-desktop/current".into(), format!("{name}\n"));
    edits.insert(".local/state/bleach-desktop/pending".into(), format!("{name}\n"));
    if replacement.is_some() {
        edits.insert(".local/share/bleach-desktop/appearance.json".into(), format!("{}\n", appearance.dump()));
    }
    for relative in edits.keys() { fsutil::reject_links(&app.home.join(relative), &app.home)?; }
    let backup = snapshots::create(app)?;
    fsutil::reject_links(&app.data, &app.home)?;
    fsutil::reject_links(&app.state, &app.home)?;
    write_transaction(app, &edits)?;
    let mut online = false;
    if !app.offline {
        let script = format!("var ds=desktops(); for(var i=0;i<ds.length;++i){{ds[i].wallpaperPlugin='org.kde.image';ds[i].currentConfigGroup=['Wallpaper','org.kde.image','General'];ds[i].writeConfig('Image',{});}}\n{}",json::quote(&uri(&image)),include_str!("../assets/panel.js"));
        if let Ok((true,text)) = run("qdbus6", &["org.kde.plasmashell","/PlasmaShell","org.kde.PlasmaShell.evaluateScript",&script])
            && !text.to_lowercase().contains("error") && !text.to_lowercase().contains("exception") {
            let path = app.home.join(".config/kdeglobals");
            fsutil::atomic_write(&path, put(&fs::read_to_string(&path).text()?,"General","ColorScheme","BreezeDark").as_bytes(),None)?;
            let colors = run("plasma-apply-colorscheme", &[&scheme,"--accent-color",accent]).map(|r|r.0).unwrap_or(false);
            fsutil::atomic_write(&path, put(&fs::read_to_string(&path).text()?,"General","ColorScheme",&scheme).as_bytes(),None)?;
            let style = run("plasma-apply-desktoptheme", &["breeze-dark"]).map(|r|r.0).unwrap_or(false);
            online = colors && style;
        }
    }
    if online { fsutil::remove_if_exists(&app.state.join("pending"))?; }
    Ok(obj! { "message" => if online { "Preset applied. Open a new terminal for its greeting." } else { "Preset saved. Desktop refresh is queued for your next KDE login." },
        "pending" => !online, "previous" => backup.get("name")?.clone() })
}

#[cfg(test)] mod tests {
    use super::*;
    #[test] fn kconfig_preserves_sections() {
        let original = "[General]\nThing=keep\nColorScheme=Old\n\n[Other]\nColorScheme=untouched\n";
        let updated = put(original,"General","ColorScheme","New");
        assert!(updated.contains("Thing=keep")); assert!(updated.contains("[Other]\nColorScheme=untouched"));
        assert_eq!(updated, put(&updated,"General","ColorScheme","New"));
    }
    #[test] fn file_uri_escapes() { assert_eq!(uri(Path::new("/tmp/a b#雪.png")), "file:///tmp/a%20b%23%E9%9B%AA.png"); }
}
