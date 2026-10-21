mod json;
mod fsutil;
mod presets;
mod portraits;
mod appearance;
mod custom_presets;
mod snapshots;
#[cfg(test)] mod tests;
use std::{ffi::{CStr,CString,c_char}, fs, io::{Read,Write}, path::PathBuf};
use json::Value;
use fsutil::{Result,TextResult};

pub struct App {
    home: PathBuf, data: PathBuf, state: PathBuf, snapshots: PathBuf, wallpapers: PathBuf,
    catalog: Value, offline: bool,
}
impl App {
    fn new(home: PathBuf, offline: bool) -> Result<Self> {
        if !home.is_absolute() || home.parent().is_none() { return Err("Use an absolute home directory".into()); }
        Ok(Self { data:home.join(".local/share/bleach-desktop"), state:home.join(".local/state/bleach-desktop"),
            snapshots:home.join("Backups/Bleach-Desktop"), wallpapers:home.join("Pictures/Bleach-TYBW/Wallpapers"), home,
            catalog:json::parse(include_str!("../assets/catalog.json"))?, offline })
    }
    fn environment() -> Result<Self> {
        let staging = std::env::var_os("BANKAI_HOME");
        let home = staging.clone().or_else(||std::env::var_os("HOME")).ok_or("HOME is unset")?;
        Self::new(PathBuf::from(home), staging.is_some() || std::env::var_os("BANKAI_OFFLINE").is_some())
    }
    fn preset(&self, name: &str) -> Result<&Value> {
        self.catalog.get("presets")?.array()?.iter().find(|p| p.get("id").and_then(Value::text).ok() == Some(name)).ok_or_else(||format!("Unknown preset: {name}"))
    }
    fn current(&self) -> Result<String> {
        let path = self.data.join("current");
        fsutil::reject_links(&path, &self.home)?;
        let current = match fs::read_to_string(path) {
            Ok(current) => current,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok("tybw".into()),
            Err(error) => return Err(error.to_string()),
        };
        if self.preset(current.trim()).is_ok() { Ok(current.trim().into()) } else { Ok("tybw".into()) }
    }
    fn dispatch(&self, request: &Value) -> Result<Value> {
        let op = request.get("op")?.text()?;
        match op {
            "bootstrap" => {
                fsutil::reject_links(&self.state, &self.home)?;
                let (saved_presets, saved_presets_error) = match custom_presets::list(self) {
                    Ok(rows) => (Value::from(rows), Value::from("")),
                    Err(error) => (Value::from(Vec::<Value>::new()), Value::from(error)),
                };
                Ok(obj! { "presets" => self.catalog.get("presets")?.clone(), "custom_presets" => saved_presets, "custom_presets_error" => saved_presets_error, "style" => include_str!("../assets/style.qss"),
                "home" => self.home.to_string_lossy().to_string(), "data" => self.data.to_string_lossy().to_string(), "version" => env!("CARGO_PKG_VERSION"),
                "mask_svg" => include_str!("../assets/bleach-tray.svg"), "terminal_svg" => include_str!("../assets/bleach-terminal.svg"), "monitor_svg" => include_str!("../assets/bleach-monitor.svg"), "backups_svg" => include_str!("../assets/bleach-backups.svg") })
            },
            "status" => Ok(obj! { "current" => self.current()?, "pending" => self.state.join("pending").exists(),
                "autostart" => self.home.join(".config/autostart/bleach-bankai-rust.desktop").exists(), "offline" => self.offline }),
            "appearance" => appearance::load(self),
            "save-appearance" => appearance::save(self,request),
            "repair-appearance" => appearance::repair(self),
            "reset-appearance" => appearance::reset(self),
            "custom-presets" => Ok(Value::from(custom_presets::list(self)?)),
            "save-custom-preset" => custom_presets::save(self,request),
            "delete-custom-preset" => custom_presets::delete(self,request),
            "apply-custom-preset" => custom_presets::apply(self,request),
            "shuffle-login" => appearance::shuffle_login(self),
            "portraits" => portraits::status(self),
            "save-portraits" => portraits::save(self, request),
            "snapshots" => { let _lock = fsutil::Lock::acquire(&self.state)?; Ok(Value::from(snapshots::scan(self)?)) },
            "plan" => { let _lock = fsutil::Lock::acquire(&self.state)?; snapshots::plan(self,usize::try_from(request.get("keep")?.number()?).text()?) },
            "apply" => presets::apply(self,request.get("preset")?.text()?),
            "backup" | "verify" | "restore" | "protect" | "cleanup" => snapshots::locked_dispatch(self,op,request),
            "autostart" => {
                let path = self.home.join(".config/autostart/bleach-bankai-rust.desktop"); fsutil::reject_links(&path,&self.home)?;
                if request.get("enabled")?.boolean()? {
                    let exe = std::env::current_exe().text()?;
                    let escaped = exe.to_string_lossy().replace('\\',"\\\\").replace('"',"\\\"").replace('%',"%%").replace('`',"\\`").replace('$',"\\$");
                    fsutil::atomic_write(&path,format!("[Desktop Entry]\nType=Application\nName=Bankai Rust tray\nExec=\"{escaped}\" tray\nOnlyShowIn=KDE;\nNoDisplay=true\nX-KDE-autostart-phase=2\n").as_bytes(),Some(0o644))?;
                } else { fsutil::remove_if_exists(&path)?; }
                Ok(obj! { "message" => "Rust login startup preference saved." })
            }
            _ => Err(format!("Unknown operation: {op}")),
        }
    }
}
fn response(request: &str) -> Value {
    match json::parse(request).and_then(|req|App::environment()?.dispatch(&req)) {
        Ok(value) => obj! { "ok" => true, "result" => value },
        Err(error) => obj! { "ok" => false, "error" => error },
    }
}
// These two exports are the ownership boundary: C++ frees only strings returned here.
#[unsafe(no_mangle)]
/// Dispatch one JSON request across the C ABI and return its JSON response.
///
/// # Safety
/// `request` must be null or point to a readable, NUL-terminated C string that
/// remains valid for the duration of this call.
pub unsafe extern "C" fn bankai_request(request: *const c_char) -> *mut c_char {
    let result = std::panic::catch_unwind(|| {
        if request.is_null() { return obj! { "ok" => false, "error" => "Null request" }.dump(); }
        let text = unsafe { CStr::from_ptr(request) }.to_string_lossy(); response(&text).dump()
    }).unwrap_or_else(|_|obj! { "ok" => false, "error" => "Unexpected Rust error" }.dump());
    CString::new(result).unwrap().into_raw()
}
#[unsafe(no_mangle)]
/// Release a response string returned by [`bankai_request`].
///
/// # Safety
/// `value` must be null or the exact pointer returned by [`bankai_request`],
/// and it must not have been freed already.
pub unsafe extern "C" fn bankai_free(value: *mut c_char) {
    if !value.is_null() { drop(unsafe { CString::from_raw(value) }); }
}
unsafe extern "C" { fn bankai_gui(argc: i32, argv: *mut *mut c_char) -> i32; }
fn main() {
    let args:Vec<String> = std::env::args().collect();
    let result = cli(&args);
    match result { Ok(code) => std::process::exit(code), Err(error) => { eprintln!("bankai-rust: {error}"); std::process::exit(1); } }
}
fn cli(args: &[String]) -> Result<i32> {
    let action = args.get(1).map(String::as_str).unwrap_or("open");
    if action == "--version" { println!("Bankai Rust {} · Rust core + native Qt",env!("CARGO_PKG_VERSION")); return Ok(0); }
    if matches!(action,"--help"|"-h") {
        println!("Bankai\n\n  bankai [open|tray|backups]\n  bankai <character>\n  bankai status\n  bankai backup\n  bankai verify <snapshot>\n  bankai restore [snapshot]\n  bankai cleanup-plan [keep]\n  bankai --version\n\nThe Rust executable is also available as bankai-rust. The Python edition is bankai-python. BANKAI_HOME selects an isolated staging home and disables live KDE commands."); return Ok(0);
    }
    if action == "--rpc" {
        let mut bytes = vec![]; std::io::stdin().take(16*1024*1024+1).read_to_end(&mut bytes).text()?;
        if bytes.len()>16*1024*1024 { return Err("RPC request too large".into()); }
        let result = response(&String::from_utf8(bytes).text()?);
        println!("{}",result.dump()); return Ok(if result.get("ok")?.boolean()? {0} else {1});
    }
    if matches!(action,"open"|"tray"|"backups"|"--smoke-test"|"--benchmark") {
        let strings:Vec<CString> = args.iter().map(|a|CString::new(a.as_bytes()).text()).collect::<Result<_>>()?;
        let mut pointers:Vec<*mut c_char> = strings.iter().map(|s|s.as_ptr() as *mut c_char).collect(); pointers.push(std::ptr::null_mut());
        return Ok(unsafe { bankai_gui(strings.len() as i32,pointers.as_mut_ptr()) });
    }
    let app = App::environment()?;
    let request = match action {
        "status" => obj! { "op" => "status" }, "backup" => obj! { "op" => "backup" },
        "verify" | "restore" => obj! { "op" => action, "name" => args.get(2).map(String::as_str).unwrap_or(snapshots::BASELINE) },
        "shuffle-login" => obj! { "op" => "shuffle-login" },
        "cleanup-plan" => obj! { "op" => "plan", "keep" => args.get(2).map(String::as_str).unwrap_or("5").parse::<u64>().text()? },
        _ if app.preset(action).is_ok() => obj! { "op" => "apply", "preset" => action },
        _ => return Err("Unknown command. Run bankai --help.".into()),
    };
    let result = app.dispatch(&request)?;
    if let Some(message) = result.opt("message") { println!("{}",message.text()?); }
    else { println!("{}",result.dump()); }
    std::io::stdout().flush().text()?;
    Ok(0)
}
