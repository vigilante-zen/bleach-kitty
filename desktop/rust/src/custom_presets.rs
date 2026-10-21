use std::{collections::BTreeSet, fs, time::{SystemTime, UNIX_EPOCH}};
use crate::{App, json::Value, obj, fsutil::{self, Result, TextResult, Lock}};

fn path(app: &App) -> std::path::PathBuf { app.data.join("custom-presets.json") }
pub fn list(app: &App) -> Result<Vec<Value>> {
    let path=path(app); fsutil::reject_links(&path,&app.home)?;
    let rows=match fs::read_to_string(path) { Ok(text)=>crate::json::parse(&text)?.array()?.clone(), Err(e) if e.kind()==std::io::ErrorKind::NotFound=>vec![], Err(e)=>return Err(e.to_string()) };
    if rows.len()>50{return Err("At most 50 custom presets are supported".into());}
    let mut ids=BTreeSet::new(); let mut names=BTreeSet::new();
    for row in &rows {
        let id=row.get("id")?.text()?; let name=row.get("name")?.text()?; let base=row.get("preset")?.text()?;
        let accent=row.get("accent")?.text()?; let login=row.get("login")?.text()?; let edition=row.get("edition")?.text()?;
        if !id.starts_with("custom-") || !ids.insert(id.to_string()) {return Err("Invalid or duplicate custom preset id".into());}
        if name.trim().is_empty() || name.chars().count()>40 || !names.insert(name.to_lowercase()) {return Err("Invalid or duplicate custom preset name".into());}
        app.preset(base)?; if login!="follow"{app.preset(login)?;}
        if !matches!(edition,"color"|"manga") {return Err("Invalid custom preset wallpaper edition".into());}
        if !accent.is_empty() && (accent.len()!=7 || !accent.starts_with('#') || !accent.as_bytes()[1..].iter().all(u8::is_ascii_hexdigit)) {return Err("Invalid custom preset accent".into());}
    }
    Ok(rows)
}
pub fn save(app: &App, request: &Value) -> Result<Value> {
    let name=request.get("name")?.text()?.trim();
    if name.is_empty() || name.chars().count()>40{return Err("Preset names must be 1–40 characters".into());}
    let base=request.get("preset")?.text()?; app.preset(base)?;
    let accent=request.get("accent")?.text()?;
    if !accent.is_empty() && (accent.len()!=7 || !accent.starts_with('#') || !accent.as_bytes()[1..].iter().all(u8::is_ascii_hexdigit)){return Err("Accent must be empty or a six-digit hex color".into());}
    let login=request.get("login")?.text()?; if login!="follow"{app.preset(login)?;}
    let edition=request.get("edition")?.text()?; if !matches!(edition,"color"|"manga"){return Err("Choose color or manga wallpaper".into());}
    let _lock=Lock::acquire(&app.state)?; let mut rows=list(app)?;
    if rows.len()>=50{return Err("You can save up to 50 custom presets".into());}
    if rows.iter().any(|r|r.get("name").and_then(Value::text).is_ok_and(|n|n.eq_ignore_ascii_case(name))){return Err("A saved preset already has that name".into());}
    let stamp=SystemTime::now().duration_since(UNIX_EPOCH).text()?.as_nanos();
    let row=obj!{"id"=>format!("custom-{stamp:x}"),"name"=>name,"preset"=>base,"accent"=>accent,"login"=>login,"edition"=>edition};
    rows.push(row.clone()); fsutil::atomic_write(&path(app),format!("{}\n",Value::from(rows).dump()).as_bytes(),None)?; Ok(row)
}
pub fn delete(app:&App,request:&Value)->Result<Value>{
    let id=request.get("id")?.text()?; let _lock=Lock::acquire(&app.state)?; let mut rows=list(app)?;
    let old=rows.len(); rows.retain(|r|r.get("id").and_then(Value::text).ok()!=Some(id));
    if rows.len()==old{return Err("Saved preset not found".into());}
    fsutil::atomic_write(&path(app),format!("{}\n",Value::from(rows).dump()).as_bytes(),None)?; Ok(obj!{"message"=>"Custom preset deleted."})
}
pub fn apply(app:&App,request:&Value)->Result<Value>{
    let id=request.get("id")?.text()?; let row=list(app)?.into_iter().find(|r|r.get("id").and_then(Value::text).ok()==Some(id)).ok_or("Saved preset not found")?;
    let old=crate::appearance::load(app)?;
    let options=obj!{"edition"=>row.get("edition")?.clone(),"accent"=>row.get("accent")?.clone(),"login"=>row.get("login")?.clone(),"shuffle_login"=>old.get("shuffle_login")?.clone(),"pool"=>old.get("pool")?.clone()};
    crate::appearance::save(app,&obj!{"appearance"=>options})?;
    crate::presets::apply(app,row.get("preset")?.text()?)
}
