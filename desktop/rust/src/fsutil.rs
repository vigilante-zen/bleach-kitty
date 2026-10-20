use std::{fs::{self, File, OpenOptions}, io::{Read, Write}, os::fd::AsRawFd, os::unix::fs::PermissionsExt, path::{Component, Path, PathBuf}, time::{SystemTime, UNIX_EPOCH}};
use crate::json::{self, Value};
pub type Result<T> = std::result::Result<T, String>;
pub trait TextResult<T> { fn text(self) -> Result<T>; }
impl<T, E: std::fmt::Display> TextResult<T> for std::result::Result<T,E> {
    fn text(self) -> Result<T> { self.map_err(|e| e.to_string()) }
}
unsafe extern "C" {
    fn flock(fd: i32, op: i32) -> i32;
    fn bankai_hash_file(path: *const std::ffi::c_char, output: *mut u8) -> bool;
    fn bankai_hash_bytes(data: *const u8, length: usize, output: *mut u8);
    fn bankai_timestamp(output: *mut u8, capacity: usize) -> usize;
}
pub struct Lock(File);
impl Lock {
    pub fn acquire(state: &Path) -> Result<Self> {
        fs::create_dir_all(state).text()?;
        reject_links(state, state)?;
        let path = state.join("snapshot-management.lock");
        reject_links(&path, state)?;
        let file = OpenOptions::new().create(true).append(true).open(path).text()?;
        if unsafe { flock(file.as_raw_fd(), 2) } != 0 { return Err(std::io::Error::last_os_error().to_string()); }
        Ok(Self(file))
    }
}
impl Drop for Lock { fn drop(&mut self) { unsafe { flock(self.0.as_raw_fd(), 8); } } }

pub fn valid_relative(path: &str) -> bool {
    !path.is_empty() && !Path::new(path).is_absolute()
        && Path::new(path).components().all(|p| matches!(p, Component::Normal(_)))
        && !path.split('/').any(|p| p.is_empty() || p == "." || p == "..")
}
pub fn reject_links(path: &Path, boundary: &Path) -> Result<()> {
    if !path.starts_with(boundary) { return Err("Path escapes its allowed directory".into()); }
    let mut current = Some(path);
    while let Some(p) = current {
        match fs::symlink_metadata(p) {
            Ok(meta) if meta.file_type().is_symlink() => return Err(format!("Symlinks are unsupported: {}", p.display())),
            Ok(_) => (),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
            Err(e) => return Err(e.to_string()),
        }
        if p == boundary { break; }
        current = p.parent();
    }
    Ok(())
}
pub fn walk(root: &Path) -> Result<Vec<PathBuf>> {
    let mut files = vec![];
    if !root.exists() { reject_links(root, root)?; return Ok(files); }
    fn visit(path: &Path, files: &mut Vec<PathBuf>) -> Result<()> {
        let meta = fs::symlink_metadata(path).text()?;
        if meta.file_type().is_symlink() { return Err(format!("Contains a symlink: {}", path.display())); }
        if meta.is_file() { files.push(path.to_path_buf()); }
        else if meta.is_dir() {
            let mut children = fs::read_dir(path).text()?.collect::<std::io::Result<Vec<_>>>().text()?;
            children.sort_by_key(|p| p.file_name());
            for child in children { visit(&child.path(), files)?; }
        } else { return Err(format!("Contains a special file: {}", path.display())); }
        Ok(())
    }
    visit(root, &mut files)?; Ok(files)
}
pub fn atomic_write(path: &Path, bytes: &[u8], mode: Option<u32>) -> Result<()> {
    let parent = path.parent().ok_or("Missing parent directory")?;
    fs::create_dir_all(parent).text()?;
    reject_links(path, parent)?;
    let old_mode = fs::metadata(path).ok().map(|m| m.permissions().mode() & 0o777);
    let temp = parent.join(format!(".bankai-{}-{}", std::process::id(), nonce()));
    let result = (|| {
        let mut file = OpenOptions::new().create_new(true).write(true).open(&temp).text()?;
        file.set_permissions(fs::Permissions::from_mode(mode.or(old_mode).unwrap_or(0o600))).text()?;
        file.write_all(bytes).text()?; file.sync_all().text()?;
        fs::rename(&temp, path).text()
    })();
    if temp.exists() { let _ = fs::remove_file(temp); }
    result
}
pub fn nonce() -> u128 { SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_nanos() }
pub fn timestamp() -> String {
    let mut buffer = [0u8; 64];
    let length = unsafe { bankai_timestamp(buffer.as_mut_ptr(), buffer.len()) };
    let date = String::from_utf8_lossy(&buffer[..length.min(buffer.len())]);
    format!("{date}-{:06}", nonce() / 1000 % 1_000_000)
}
pub fn hash(path: &Path) -> Result<String> {
    use std::os::unix::ffi::OsStrExt;
    let cpath = std::ffi::CString::new(path.as_os_str().as_bytes()).text()?;
    let mut output = [0u8; 65];
    if !unsafe { bankai_hash_file(cpath.as_ptr(), output.as_mut_ptr()) } { return Err(format!("Could not hash {}", path.display())); }
    String::from_utf8(output[..64].to_vec()).text()
}
pub fn hash_bytes(data: &[u8]) -> String {
    let mut output = [0u8;65];
    unsafe { bankai_hash_bytes(data.as_ptr(), data.len(), output.as_mut_ptr()); }
    String::from_utf8_lossy(&output[..64]).to_string()
}
pub fn read_json(path: &Path) -> Result<Value> {
    let mut bytes = vec![];
    File::open(path).text()?.take(16 * 1024 * 1024 + 1).read_to_end(&mut bytes).text()?;
    if bytes.len() > 16 * 1024 * 1024 { return Err("JSON file exceeds the size limit".into()); }
    json::parse(&String::from_utf8(bytes).text()?)
}
pub fn remove_if_exists(path: &Path) -> Result<()> {
    match fs::remove_file(path) { Ok(()) => Ok(()), Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()), Err(e) => Err(e.to_string()) }
}
