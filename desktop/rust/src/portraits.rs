use std::fs;
use crate::{App, json::Value, obj, fsutil::{self, Result, TextResult, Lock}};

pub fn status(app: &App) -> Result<Value> {
    let root = app.home.join(".config/fastfetch");
    let directory = root.join("portraits");
    fsutil::reject_links(&directory, &app.home)?;
    let mut names = vec![];
    if directory.exists() {
        for entry in fs::read_dir(&directory).text()? {
            let path = entry.text()?.path();
            if path.extension().and_then(|s| s.to_str()) == Some("png") {
                fsutil::reject_links(&path, &app.home)?;
                if path.is_file()
                    && let Some(name) = path.file_stem().and_then(|s| s.to_str())
                    && valid_name(name)
                {
                    names.push(name.to_string());
                }
            }
        }
    }
    names.sort();
    let read = |name: &str, fallback: &str| -> Result<String> {
        let path = root.join(name);
        fsutil::reject_links(&path, &app.home)?;
        match fs::read_to_string(path) {
            Ok(value) => Ok(value.trim().to_string()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(fallback.to_string()),
            Err(e) => Err(e.to_string()),
        }
    };
    let choice = read("portrait-choice", "random")?;
    let art = read("portrait-art-mode", "color")?;
    Ok(obj! { "choice" => if names.contains(&choice) { choice } else { "random".into() },
        "art" => if matches!(art.as_str(), "color" | "manga" | "mixed") { art } else { "color".into() },
        "match_desktop" => read("portrait-follow-desktop", "off")? == "on",
        "portraits" => Value::from(names.into_iter().map(Value::from).collect::<Vec<_>>()) })
}
fn valid_name(name: &str) -> bool {
    !name.is_empty() && name.bytes().all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == b'-')
}
pub fn save(app: &App, request: &Value) -> Result<Value> {
    let requested = request.get("choice")?.text()?;
    let follow = request.opt("match_desktop").map(Value::boolean).transpose()?.unwrap_or(false);
    let art = request.get("art")?.text()?;
    if !matches!(art, "color" | "manga" | "mixed") { return Err("Choose color, manga or mixed art.".into()); }
    fsutil::reject_links(&app.state, &app.home)?;
    let _lock = Lock::acquire(&app.state)?;
    let desktop = app.current();
    let choice = if follow { app.preset(&desktop)?.get("portrait")?.text()? } else { requested };
    let current = status(app)?;
    if choice != "random" && (!valid_name(choice) || !current.get("portraits")?.array()?.iter().any(|v| v.text().ok() == Some(choice))) {
        return Err("Choose an installed portrait or random rotation.".into());
    }
    let root = app.home.join(".config/fastfetch");
    for name in ["portrait-choice", "portrait-art-mode", "portrait-follow-desktop"] { fsutil::reject_links(&root.join(name), &app.home)?; }
    fsutil::atomic_write(&root.join("portrait-choice"), format!("{choice}\n").as_bytes(), None)?;
    fsutil::atomic_write(&root.join("portrait-art-mode"), format!("{art}\n").as_bytes(), None)?;
    fsutil::atomic_write(&root.join("portrait-follow-desktop"), if follow { b"on\n" } else { b"off\n" }, None)?;
    Ok(obj! { "message" => "Terminal artwork saved. Open a new terminal tab to see it." })
}
