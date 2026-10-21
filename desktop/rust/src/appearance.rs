use std::fs;
use crate::{App, json::Value, obj, fsutil::{self, Result, TextResult}};

pub fn defaults(app: &App) -> Result<Value> {
    Ok(obj! { "edition" => "color", "accent" => "", "login" => "follow", "shuffle_login" => false,
        "pool" => Value::from(app.catalog.get("presets")?.array()?.iter().map(|p|p.get("id").unwrap().clone()).collect::<Vec<_>>()) })
}
pub fn validate(app: &App, value: &Value) -> Result<Value> {
    let edition = value.get("edition")?.text()?;
    if !matches!(edition, "color" | "manga") { return Err("Choose color or manga backgrounds".into()); }
    let accent = value.get("accent")?.text()?;
    if !accent.is_empty() && (accent.len()!=7 || !accent.starts_with('#') || !accent.as_bytes()[1..].iter().all(u8::is_ascii_hexdigit)) {
        return Err("Accent must be empty or a six-digit hex color, such as #a9dfff".into());
    }
    let login = value.get("login")?.text()?;
    if login != "follow" { app.preset(login)?; }
    let shuffle = value.get("shuffle_login")?.boolean()?;
    let pool = value.get("pool")?.array()?;
    if pool.is_empty() { return Err("Choose at least one character for the shuffle pool".into()); }
    let mut seen = std::collections::BTreeSet::new();
    for row in pool { let id=row.text()?; app.preset(id)?; if !seen.insert(id) {return Err("Duplicate shuffle character".into());} }
    Ok(obj! { "edition" => edition, "accent" => accent, "login" => login, "shuffle_login" => shuffle, "pool" => Value::from(pool.clone()) })
}
pub fn load(app: &App) -> Result<Value> {
    let path=app.data.join("appearance.json"); fsutil::reject_links(&path,&app.home)?;
    match fs::read_to_string(path) {
        Ok(text)=>validate(app,&crate::json::parse(&text)?),
        Err(e) if e.kind()==std::io::ErrorKind::NotFound=>defaults(app),
        Err(e)=>Err(e.to_string())
    }
}
pub fn save(app: &App, request: &Value) -> Result<Value> {
    let value=validate(app,request.get("appearance")?)?;
    let path=app.data.join("appearance.json"); fsutil::reject_links(&path,&app.home)?;
    let _lock=fsutil::Lock::acquire(&app.state)?;
    fsutil::atomic_write(&path,format!("{}\n",value.dump()).as_bytes(),None)?;
    Ok(obj! {"message"=>"Appearance saved. Apply a background to update wallpaper and accents. Login choice syncs after system setup."})
}
pub fn reset(app: &App) -> Result<Value> {
    let previous = load(app)?;
    save(app, &obj! { "appearance" => defaults(app)? })?;
    match crate::presets::apply(app, "tybw") {
        Ok(mut result) => {
            if let Value::Object(ref mut fields) = result {
                fields.insert("message".into(), Value::from("Appearance settings and desktop reset to Bankai defaults."));
            }
            Ok(result)
        }
        Err(error) => {
            if let Err(restore_error) = save(app, &obj! { "appearance" => previous }) {
                return Err(format!("{error}; failed to restore previous appearance settings: {restore_error}"));
            }
            Err(error)
        }
    }
}
pub fn shuffle_login(app: &App) -> Result<Value> {
    let value=load(app)?;
    if !value.get("shuffle_login")?.boolean()? {return Ok(obj!{"message"=>"Login shuffle is disabled."});}
    let current=app.current()?;
    let all=value.get("pool")?.array()?;
    let mut pool=all.iter().filter(|v|v.text().ok()!=Some(current.as_str())).collect::<Vec<_>>();
    if pool.is_empty(){pool=all.iter().collect();}
    use std::io::Read;
    let mut random=fs::File::open("/dev/urandom").text()?;
    let selected=loop {
        let mut bytes=[0u8;8]; random.read_exact(&mut bytes).text()?;
        if let Some(index)=random_index(u64::from_ne_bytes(bytes),pool.len()) {
            break pool[index].text()?;
        }
    };
    crate::presets::apply(app,selected)
}

fn random_index(value: u64, length: usize) -> Option<usize> {
    let length=u64::try_from(length).ok()?;
    if length==0 { return None; }
    let threshold=length.wrapping_neg()%length;
    (value>=threshold).then_some((value%length) as usize)
}

#[cfg(test)]
mod tests {
    use super::random_index;

    #[test]
    fn random_index_rejects_the_incomplete_range() {
        assert_eq!(random_index(0,3),None);
        assert_eq!(random_index(1,3),Some(1));
        assert_eq!(random_index(2,3),Some(2));
        assert_eq!(random_index(3,3),Some(0));
        assert_eq!(random_index(u64::MAX,3),Some(0));
    }

    #[test]
    fn random_index_handles_empty_and_single_entry_pools() {
        assert_eq!(random_index(0,0),None);
        assert_eq!(random_index(0,1),Some(0));
        assert_eq!(random_index(u64::MAX,1),Some(0));
    }
}
