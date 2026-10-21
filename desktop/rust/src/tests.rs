use super::*;
use std::ffi::CString;
use std::{os::unix::fs::{PermissionsExt,symlink},path::Path};

fn make_fifo(path:&Path){
    use std::os::unix::ffi::OsStrExt;
    unsafe extern "C" {fn mkfifo(path:*const std::os::raw::c_char,mode:u32)->i32;}
    let path=CString::new(path.as_os_str().as_bytes()).unwrap();
    assert_eq!(unsafe{mkfifo(path.as_ptr(),0o600)},0);
}

struct Fixture { app:App }
impl Fixture {
    fn new()->Self {
        let home=std::env::temp_dir().join(format!("bankai-rust-test-{}-{}",std::process::id(),fsutil::nonce()));
        fs::create_dir_all(&home).unwrap();let app=App::new(home,true).unwrap();
        write(&app.home.join(".config/kitty/kitty.conf"),"font_size 12\n");
        write(&app.home.join(".config/plasma-org.kde.plasma.desktop-appletsrc"),"[Containments][202]\nplugin=org.kde.plasma.folder\n\n[Containments][202][Wallpaper][org.kde.image][General]\nImage=old\n\n[Containments][203]\nplugin=org.kde.plasma.folder\n");
        write(&app.home.join(".config/kdeglobals"),"[General]\nUnrelated=preserved\n");
        for p in app.catalog.get("presets").unwrap().array().unwrap(){
            write(&app.wallpapers.join(p.get("image").unwrap().text().unwrap()),"fake wallpaper content");
            write(&app.home.join(".local/share/color-schemes").join(format!("Bleach{}.colors",p.get("title").unwrap().text().unwrap())),"[Colors:Window]\nForegroundNormal=232,237,245\n");
        }
        Self{app}
    }
}
impl Drop for Fixture{fn drop(&mut self){let _=fs::remove_dir_all(&self.app.home);}}
fn write(path:&Path,text:&str){fs::create_dir_all(path.parent().unwrap()).unwrap();fs::write(path,text).unwrap();}
fn snapshot(f:&Fixture)->String{snapshots::create(&f.app).unwrap().get("name").unwrap().text().unwrap().into()}
fn rename_snapshot(f:&Fixture,name:&str){let created=snapshot(f);fs::rename(f.app.snapshots.join(created),f.app.snapshots.join(name)).unwrap();}

#[test] fn catalog_is_valid() {
    let app=App::new(PathBuf::from("/tmp/bankai-test"),true).unwrap();
    assert_eq!(app.catalog.get("presets").unwrap().array().unwrap().len(),18);
    assert!(snapshots::allowed(&app,".config/kitty/kitty.conf"));
    assert!(!snapshots::allowed(&app,".config/kitty/../../.ssh/id_rsa"));
    assert!(!snapshots::allowed(&app,".ssh/id_rsa"));
    assert!(!snapshots::allowed(&app,".config/fish/functions/bankai-x/secret.fish"));
}

#[test]
fn current_preset_rejects_symlinked_state_and_defaults_missing_or_invalid_values() {
    let f=Fixture::new();
    assert_eq!(f.app.current().unwrap(),"tybw");
    write(&f.app.data.join("current"),"urahara\n");
    assert_eq!(f.app.current().unwrap(),"urahara");
    write(&f.app.data.join("current"),"not-a-preset\n");
    assert_eq!(f.app.current().unwrap(),"tybw");
    fs::remove_file(f.app.data.join("current")).unwrap();
    let outside=f.app.home.join("external-current");
    write(&outside,"urahara\n");
    symlink(&outside,f.app.data.join("current")).unwrap();
    assert!(f.app.current().is_err());
}

#[test]
fn bootstrap_reports_invalid_custom_presets_without_hiding_the_problem() {
    let f=Fixture::new();
    write(&f.app.data.join("custom-presets.json"),"not valid json");
    let bootstrap=f.app.dispatch(&obj!{"op"=>"bootstrap"}).unwrap();
    assert!(bootstrap.get("custom_presets").unwrap().array().unwrap().is_empty());
    assert!(bootstrap.get("custom_presets_error").unwrap().text().unwrap().contains("Invalid JSON"));
}

#[test]
fn bootstrap_rejects_symlinked_state_ancestors_before_gui_startup() {
    let f=Fixture::new();
    let local=f.app.home.join(".local");fs::create_dir_all(&local).unwrap();
    let outside=f.app.home.join("external-state");fs::create_dir_all(&outside).unwrap();
    symlink(&outside,local.join("state")).unwrap();
    assert!(f.app.dispatch(&obj!{"op"=>"bootstrap"}).unwrap_err().contains("Symlinks are unsupported"));
    assert!(!outside.join("bleach-desktop").exists());
}

#[test]
fn stale_appearance_save_does_not_replace_newer_shared_preferences() {
    let f=Fixture::new();
    let expected=appearance::load(&f.app).unwrap();
    let newer=obj!{"edition"=>"manga","accent"=>"#123456","login"=>"rukia","shuffle_login"=>true,"pool"=>Value::from(vec![Value::from("rukia")])};
    appearance::save(&f.app,&obj!{"appearance"=>newer.clone()}).unwrap();
    let error=appearance::save(&f.app,&obj!{"appearance"=>expected.clone(),"expected"=>expected}).unwrap_err();
    assert!(error.contains("changed in another Bankai window"));
    assert_eq!(appearance::load(&f.app).unwrap(),newer);
}
#[test]
fn appearance_repair_preserves_corrupt_file_before_restoring_defaults() {
    let f=Fixture::new();let path=f.app.data.join("appearance.json");write(&path,"not valid json\n");
    f.app.dispatch(&obj!{"op"=>"repair-appearance"}).unwrap();
    assert_eq!(appearance::load(&f.app).unwrap(),appearance::defaults(&f.app).unwrap());
    let backups=fs::read_dir(&f.app.data).unwrap().filter_map(|row|row.ok()).filter(|row|row.file_name().to_string_lossy().starts_with("appearance.json.corrupt-")).collect::<Vec<_>>();
    assert_eq!(backups.len(),1);assert_eq!(fs::read_to_string(backups[0].path()).unwrap(),"not valid json\n");
    let current=obj!{"edition"=>"manga","accent"=>"#123456","login"=>"rukia","shuffle_login"=>false,"pool"=>appearance::defaults(&f.app).unwrap().get("pool").unwrap().clone()};
    appearance::save(&f.app,&obj!{"appearance"=>current.clone()}).unwrap();
    assert!(f.app.dispatch(&obj!{"op"=>"repair-appearance"}).unwrap_err().contains("readable again"));
    assert_eq!(appearance::load(&f.app).unwrap(),current);
    let path=f.app.data.join("appearance.json");fs::remove_file(&path).unwrap();let outside=f.app.home.join("external-appearance.json");write(&outside,"keep me");symlink(&outside,&path).unwrap();
    assert!(f.app.dispatch(&obj!{"op"=>"repair-appearance"}).unwrap_err().contains("Symlinks are unsupported"));
    assert_eq!(fs::read_to_string(outside).unwrap(),"keep me");assert!(path.is_symlink());
}
#[test]
fn preset_write_transaction_rolls_back_after_a_midway_failure() {
    let f=Fixture::new();let first=f.app.home.join(".config/a-first");write(&first,"original");
    write(&f.app.data.join("current"),"old\n");write(&f.app.state.join("pending"),"old pending\n");write(&f.app.data.join("appearance.json"),"old appearance\n");
    let edits=std::collections::BTreeMap::from([
        (".config/a-first".to_string(),"updated".to_string()),
        (".config/z-second".to_string(),"new file".to_string()),
        (".local/share/bleach-desktop/appearance.json".to_string(),"new appearance\n".to_string()),
        (".local/share/bleach-desktop/current".to_string(),"new preset\n".to_string()),
        (".local/state/bleach-desktop/pending".to_string(),"new preset\n".to_string()),
    ]);
    let mut writes=0;
    let error=presets::write_transaction_with(&f.app,&edits,|path,bytes|{
        writes+=1;
        if writes==5 { Err("injected write failure".into()) }
        else { fsutil::atomic_write(path,bytes,None) }
    }).unwrap_err();
    assert!(error.contains("injected write failure"));
    assert_eq!(fs::read_to_string(first).unwrap(),"original");
    assert!(!f.app.home.join(".config/z-second").exists());
    assert_eq!(fs::read_to_string(f.app.data.join("appearance.json")).unwrap(),"old appearance\n");
    assert_eq!(fs::read_to_string(f.app.data.join("current")).unwrap(),"old\n");
    assert_eq!(fs::read_to_string(f.app.state.join("pending")).unwrap(),"old pending\n");
}
#[test]
fn failed_custom_preset_apply_restores_previous_appearance_settings() {
    let f=Fixture::new();let previous=appearance::load(&f.app).unwrap();
    let row=custom_presets::save(&f.app,&obj!{"name"=>"Missing Manga","preset"=>"rukia","accent"=>"#123456","login"=>"rukia","edition"=>"manga"}).unwrap();
    let error=custom_presets::apply(&f.app,&obj!{"id"=>row.get("id").unwrap().clone()}).unwrap_err();
    assert!(error.contains("Required asset is missing"));
    assert_eq!(appearance::load(&f.app).unwrap(),previous);
    assert!(!f.app.data.join("current").exists());
}
#[test]fn hash_matches_known_sha256(){assert_eq!(fsutil::hash_bytes(b"abc"),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");let f=Fixture::new();let path=f.app.home.join("data");fs::write(&path,b"abc").unwrap();assert_eq!(fsutil::hash(&path).unwrap(),fsutil::hash_bytes(b"abc"));}
#[test]fn snapshot_round_trip_preserves_mode_and_absent_files(){
    let f=Fixture::new();let target=f.app.home.join(".config/kitty/kitty.conf");fs::set_permissions(&target,fs::Permissions::from_mode(0o640)).unwrap();let name=snapshot(&f);
    write(&target,"changed");let added=f.app.home.join(".config/fish/completions/bankai.fish");write(&added,"new file");
    snapshots::restore(&f.app,&name).unwrap();assert_eq!(fs::read_to_string(&target).unwrap(),"font_size 12\n");assert_eq!(fs::metadata(target).unwrap().permissions().mode()&0o777,0o640);assert!(!added.exists());
    assert!(fs::read_dir(&f.app.snapshots).unwrap().count()>=2);
}
#[test]
fn snapshot_restore_rolls_back_writes_and_deletions_after_a_late_failure() {
    let f=Fixture::new();
    let first=f.app.home.join(".config/kitty/restore-a");let removed=f.app.home.join(".config/kitty/restore-b");let last=f.app.home.join(".config/kitty/restore-c");
    write(&first,"first original");write(&removed,"removed original");write(&last,"last original");
    fs::set_permissions(&first,fs::Permissions::from_mode(0o640)).unwrap();
    let edits=std::collections::BTreeMap::from([
        (".config/kitty/restore-a".to_string(),Some((b"first replacement".to_vec(),0o600))),
        (".config/kitty/restore-b".to_string(),None),
        (".config/kitty/restore-c".to_string(),Some((b"last replacement".to_vec(),0o600))),
    ]);
    let mut writes=0;
    let error=snapshots::restore_transaction_with(&f.app,&edits,|path,bytes,mode|{
        writes+=1;if writes==2 { Err("injected restore failure".into()) }
        else { fsutil::atomic_write(path,bytes,Some(mode)) }
    }).unwrap_err();
    assert!(error.contains("injected restore failure"));
    assert_eq!(fs::read_to_string(&first).unwrap(),"first original");
    assert_eq!(fs::metadata(&first).unwrap().permissions().mode()&0o777,0o640);
    assert_eq!(fs::read_to_string(removed).unwrap(),"removed original");
    assert_eq!(fs::read_to_string(last).unwrap(),"last original");
}
#[test]fn corruption_prevents_restore_before_any_replacement(){
    let f=Fixture::new();let name=snapshot(&f);let active=f.app.home.join(".config/kitty/kitty.conf");write(&active,"current settings");write(&f.app.snapshots.join(&name).join("files/.config/kitty/kitty.conf"),"corrupt snapshot");
    assert!(snapshots::restore(&f.app,&name).is_err());assert_eq!(fs::read_to_string(active).unwrap(),"current settings");
}
#[test]fn traversal_manifest_is_rejected(){
    let f=Fixture::new();let name=snapshot(&f);let path=f.app.snapshots.join(&name).join("manifest.json");let mut manifest=fsutil::read_json(&path).unwrap();
    if let Value::Object(map)=&mut manifest{map.insert("files".into(),Value::from(vec![obj!{"path"=>"../outside","mode"=>0o600u64,"sha256"=>"bad"}]));}
    fs::write(&path,manifest.dump()).unwrap();assert!(snapshots::verify(&f.app,&name).is_err());
}
#[test]fn boolean_snapshot_version_is_not_accepted_as_integer_one(){
    let f=Fixture::new();let name=snapshot(&f);let path=f.app.snapshots.join(&name).join("manifest.json");let mut manifest=fsutil::read_json(&path).unwrap();
    if let Value::Object(map)=&mut manifest{map.insert("version".into(),Value::from(true));}
    fs::write(&path,manifest.dump()).unwrap();assert!(snapshots::verify(&f.app,&name).is_err());
}
#[test]fn oversized_snapshot_manifest_is_rejected(){
    let f=Fixture::new();let name=snapshot(&f);let path=f.app.snapshots.join(&name).join("manifest.json");
    fs::write(&path,vec![b' ';fsutil::MAX_JSON_BYTES+1]).unwrap();
    assert!(snapshots::verify(&f.app,&name).unwrap_err().contains("size limit"));
}
#[test]fn fifo_snapshot_manifest_is_rejected_without_reading(){
    let f=Fixture::new();let name=snapshot(&f);let path=f.app.snapshots.join(&name).join("manifest.json");fs::remove_file(&path).unwrap();make_fifo(&path);
    assert!(snapshots::verify(&f.app,&name).unwrap_err().contains("regular file"));
}
#[test]fn fifo_snapshot_payload_is_rejected_without_hashing(){
    let f=Fixture::new();let name=snapshot(&f);let manifest=fsutil::read_json(&f.app.snapshots.join(&name).join("manifest.json")).unwrap();
    let relative=manifest.get("files").unwrap().array().unwrap()[0].get("path").unwrap().text().unwrap();let path=f.app.snapshots.join(&name).join("files").join(relative);
    fs::remove_file(&path).unwrap();make_fifo(&path);
    assert!(snapshots::verify(&f.app,&name).unwrap_err().contains("regular file"));
}
#[test]fn symlink_destination_is_rejected(){
    let f=Fixture::new();let name=snapshot(&f);let outside=f.app.home.join("outside");write(&outside,"untouched");let target=f.app.home.join(".config/kitty/kitty.conf");fs::remove_file(&target).unwrap();symlink(&outside,&target).unwrap();
    assert!(snapshots::restore(&f.app,&name).is_err());assert_eq!(fs::read_to_string(outside).unwrap(),"untouched");
}
#[test]fn all_presets_apply_offline_and_update_both_displays(){
    let f=Fixture::new();for p in f.app.catalog.get("presets").unwrap().array().unwrap(){let id=p.get("id").unwrap().text().unwrap();let result=presets::apply(&f.app,id).unwrap();assert!(result.get("pending").unwrap().boolean().unwrap());
        assert_eq!(fs::read_to_string(f.app.data.join("current")).unwrap().trim(),id);
        assert!(!f.app.home.join(".config/fastfetch/portrait-choice").exists());
        let applets=fs::read_to_string(f.app.home.join(".config/plasma-org.kde.plasma.desktop-appletsrc")).unwrap();assert_eq!(applets.matches("Image=file://").count(),2);
    }
    let kitty=fs::read_to_string(f.app.home.join(".config/kitty/kitty.conf")).unwrap();assert_eq!(kitty.matches("include themes/bleach-desktop.conf").count(),1);
    assert!(fs::read_to_string(f.app.home.join(".config/kdeglobals")).unwrap().contains("Unrelated=preserved"));
}
#[test]fn custom_preset_saves_applies_and_deletes_current_choices(){
    let f=Fixture::new();
    let previous=appearance::load(&f.app).unwrap();
    appearance::save(&f.app,&obj!{"appearance"=>previous.clone()}).unwrap();
    write(&f.app.wallpapers.join("rukia-manga.png"),"fake manga wallpaper");
    let saved=custom_presets::save(&f.app,&obj!{"name"=>"Night Rukia","preset"=>"rukia","accent"=>"#aabbcc","login"=>"ichigo","edition"=>"manga"}).unwrap();
    let id=saved.get("id").unwrap().text().unwrap();
    assert_eq!(custom_presets::list(&f.app).unwrap().len(),1);
    let applied=custom_presets::apply(&f.app,&obj!{"id"=>id}).unwrap();
    assert!(applied.get("pending").unwrap().boolean().unwrap());
    let backup_name=applied.get("previous").unwrap().text().unwrap();
    let backed_up=fsutil::read_json(&f.app.snapshots.join(backup_name).join("files/.local/share/bleach-desktop/appearance.json")).unwrap();
    assert_eq!(backed_up,previous);
    let options=appearance::load(&f.app).unwrap();
    assert_eq!(options.get("edition").unwrap().text().unwrap(),"manga");
    assert_eq!(options.get("accent").unwrap().text().unwrap(),"#aabbcc");
    assert_eq!(options.get("login").unwrap().text().unwrap(),"ichigo");
    custom_presets::delete(&f.app,&obj!{"id"=>id}).unwrap();
    assert!(custom_presets::list(&f.app).unwrap().is_empty());
}
#[test]fn reset_appearance_restores_defaults_and_applies_default_desktop(){
    let f=Fixture::new();
    appearance::save(&f.app,&obj!{"appearance"=>obj!{"edition"=>"manga","accent"=>"#123456","login"=>"rukia","shuffle_login"=>true,"pool"=>Value::from(vec![Value::from("rukia")])}}).unwrap();
    write(&f.app.home.join(".config/fastfetch/portrait-choice"),"random");
    let result=appearance::reset(&f.app).unwrap();
    assert_eq!(result.get("message").unwrap().text().unwrap(),"Appearance settings and desktop reset to Bankai defaults.");
    assert_eq!(appearance::load(&f.app).unwrap(),appearance::defaults(&f.app).unwrap());
    assert_eq!(fs::read_to_string(f.app.data.join("current")).unwrap().trim(),"tybw");
    assert!(fs::read_to_string(f.app.home.join(".config/kscreenlockerrc")).unwrap().contains("bleach-tybw.png"));
    assert_eq!(fs::read_to_string(f.app.home.join(".config/fastfetch/portrait-choice")).unwrap(),"random");
}
#[test]fn failed_appearance_reset_restores_saved_options(){
    let f=Fixture::new();
    let before=obj!{"edition"=>"manga","accent"=>"#abcdef","login"=>"rukia","shuffle_login"=>true,"pool"=>Value::from(vec![Value::from("rukia")])};
    appearance::save(&f.app,&obj!{"appearance"=>before.clone()}).unwrap();
    fs::remove_file(f.app.wallpapers.join("bleach-tybw.png")).unwrap();
    assert!(appearance::reset(&f.app).is_err());
    assert_eq!(appearance::load(&f.app).unwrap(),before);
}
#[test]fn missing_assets_do_not_change_settings(){let f=Fixture::new();fs::remove_file(f.app.wallpapers.join("urahara-desktop.png")).unwrap();assert!(presets::apply(&f.app,"urahara").is_err());assert!(!f.app.data.join("current").exists());}
#[test]fn cleanup_preserves_recent_protected_and_baseline(){
    let f=Fixture::new();for i in 0..5{rename_snapshot(&f,&format!("20261019-21000{i}-000000"));}rename_snapshot(&f,snapshots::BASELINE);snapshots::protect(&f.app,"20261019-210000-000000",true).unwrap();
    let plan=snapshots::plan(&f.app,2).unwrap();let candidates=plan.get("candidates").unwrap().array().unwrap();assert_eq!(candidates.len(),2);
    snapshots::cleanup(&f.app,&plan).unwrap();for name in [snapshots::BASELINE,"20261019-210000-000000","20261019-210003-000000","20261019-210004-000000"]{assert!(f.app.snapshots.join(name).is_dir(),"{name}");}
}
#[test]fn changes_after_review_cancel_all_deletions(){
    let f=Fixture::new();for i in 0..3{rename_snapshot(&f,&format!("20261019-21000{i}-000000"));}let plan=snapshots::plan(&f.app,1).unwrap();
    write(&f.app.snapshots.join("20261019-210000-000000/files/.config/kitty/kitty.conf"),"modified");assert!(snapshots::cleanup(&f.app,&plan).is_err());assert_eq!(fs::read_dir(&f.app.snapshots).unwrap().count(),3);
}
#[test]fn new_protection_after_review_cancels_cleanup(){let f=Fixture::new();for i in 0..3{rename_snapshot(&f,&format!("20261019-21000{i}-000000"));}let plan=snapshots::plan(&f.app,1).unwrap();snapshots::protect(&f.app,"20261019-210000-000000",true).unwrap();assert!(snapshots::cleanup(&f.app,&plan).is_err());assert_eq!(fs::read_dir(&f.app.snapshots).unwrap().count(),3);}
#[test]fn unexpected_files_and_symlinks_exclude_cleanup(){
    let f=Fixture::new();for i in 0..3{rename_snapshot(&f,&format!("20261019-21000{i}-000000"));}write(&f.app.snapshots.join("20261019-210000-000000/personal-file"),"preserve");
    symlink(f.app.home.join(".config/kdeglobals"),f.app.snapshots.join("20261019-210001-000000/link")).unwrap();assert!(snapshots::plan(&f.app,1).unwrap().get("candidates").unwrap().array().unwrap().is_empty());
}
#[test]fn invalid_absent_paths_exclude_cleanup(){
    let f=Fixture::new();rename_snapshot(&f,"20261019-210000-000000");rename_snapshot(&f,"20261019-210001-000000");
    let path=f.app.snapshots.join("20261019-210000-000000/manifest.json");let original=fsutil::read_json(&path).unwrap();
    let invalid=vec![Value::from("../outside"),Value::from(".config/kitty/kitty.conf")];
    for relative in invalid {
        let mut manifest=original.clone();
        if let Value::Object(fields)=&mut manifest {fields.insert("absent".into(),Value::from(vec![relative]));}
        fs::write(&path,manifest.dump()).unwrap();
        assert!(snapshots::plan(&f.app,1).unwrap().get("candidates").unwrap().array().unwrap().is_empty());
    }
    let mut manifest=original;
    if let Value::Object(fields)=&mut manifest {fields.insert("absent".into(),Value::from("not an array"));}
    fs::write(&path,manifest.dump()).unwrap();
    assert!(snapshots::plan(&f.app,1).unwrap().get("candidates").unwrap().array().unwrap().is_empty());
}
#[test]fn corrupt_protection_metadata_disables_cleanup(){let f=Fixture::new();write(&f.app.state.join("protected-snapshots.json"),"not json");assert!(snapshots::plan(&f.app,1).is_err());}
#[test]fn dangling_protection_metadata_symlink_disables_cleanup(){let f=Fixture::new();fs::create_dir_all(&f.app.state).unwrap();symlink(f.app.home.join("missing-protection-file"),f.app.state.join("protected-snapshots.json")).unwrap();assert!(snapshots::plan(&f.app,1).is_err());}
#[test]fn fifo_protection_metadata_disables_cleanup_without_reading(){let f=Fixture::new();fs::create_dir_all(&f.app.state).unwrap();make_fifo(&f.app.state.join("protected-snapshots.json"));assert!(snapshots::plan(&f.app,1).unwrap_err().contains("regular file"));}
#[test]fn snapshot_with_symlinked_manifest_cannot_be_protected(){let f=Fixture::new();let name=snapshot(&f);let manifest=f.app.snapshots.join(&name).join("manifest.json");let outside=f.app.home.join("outside-manifest");write(&outside,"not a manifest");fs::remove_file(&manifest).unwrap();symlink(&outside,&manifest).unwrap();assert!(snapshots::protect(&f.app,&name,true).is_err());assert!(!f.app.state.join("protected-snapshots.json").exists());}

#[test] fn portrait_preferences_validate_and_survive_presets() {
    let f = Fixture::new();
    write(&f.app.home.join(".config/fastfetch/portraits/urahara.png"), "image");
    portraits::save(&f.app, &obj! { "choice" => "random", "art" => "mixed" }).unwrap();
    presets::apply(&f.app, "ichigo").unwrap();
    let status = portraits::status(&f.app).unwrap();
    assert_eq!(status.get("choice").unwrap().text().unwrap(), "random");
    assert_eq!(status.get("art").unwrap().text().unwrap(), "mixed");
    portraits::save(&f.app, &obj! { "choice" => "urahara", "art" => "manga" }).unwrap();
    presets::apply(&f.app, "rukia").unwrap();
    assert_eq!(portraits::status(&f.app).unwrap().get("choice").unwrap().text().unwrap(), "urahara");
    for (choice, art) in [("../outside", "color"), ("missing", "color"), ("random", "invalid")] {
        assert!(portraits::save(&f.app, &obj! { "choice" => choice, "art" => art }).is_err());
    }
    assert_eq!(portraits::status(&f.app).unwrap().get("art").unwrap().text().unwrap(), "manga");
}
#[test] fn portrait_symlink_is_rejected() {
    let f = Fixture::new();
    let outside = f.app.home.join("outside"); write(&outside, "unchanged");
    let path = f.app.home.join(".config/fastfetch/portrait-art-mode");
    fs::create_dir_all(path.parent().unwrap()).unwrap(); symlink(&outside, &path).unwrap();
    assert!(portraits::save(&f.app, &obj! { "choice" => "random", "art" => "color" }).is_err());
    assert_eq!(fs::read_to_string(outside).unwrap(), "unchanged");
}
