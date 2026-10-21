use super::*;
use std::{os::unix::fs::{PermissionsExt,symlink},path::Path};

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
#[test]fn hash_matches_known_sha256(){assert_eq!(fsutil::hash_bytes(b"abc"),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");let f=Fixture::new();let path=f.app.home.join("data");fs::write(&path,b"abc").unwrap();assert_eq!(fsutil::hash(&path).unwrap(),fsutil::hash_bytes(b"abc"));}
#[test]fn snapshot_round_trip_preserves_mode_and_absent_files(){
    let f=Fixture::new();let target=f.app.home.join(".config/kitty/kitty.conf");fs::set_permissions(&target,fs::Permissions::from_mode(0o640)).unwrap();let name=snapshot(&f);
    write(&target,"changed");let added=f.app.home.join(".config/fish/completions/bankai.fish");write(&added,"new file");
    snapshots::restore(&f.app,&name).unwrap();assert_eq!(fs::read_to_string(&target).unwrap(),"font_size 12\n");assert_eq!(fs::metadata(target).unwrap().permissions().mode()&0o777,0o640);assert!(!added.exists());
    assert!(fs::read_dir(&f.app.snapshots).unwrap().count()>=2);
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
    write(&f.app.wallpapers.join("rukia-manga.png"),"fake manga wallpaper");
    let saved=custom_presets::save(&f.app,&obj!{"name"=>"Night Rukia","preset"=>"rukia","accent"=>"#aabbcc","login"=>"ichigo","edition"=>"manga"}).unwrap();
    let id=saved.get("id").unwrap().text().unwrap();
    assert_eq!(custom_presets::list(&f.app).unwrap().len(),1);
    let applied=custom_presets::apply(&f.app,&obj!{"id"=>id}).unwrap();
    assert!(applied.get("pending").unwrap().boolean().unwrap());
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
#[test]fn corrupt_protection_metadata_disables_cleanup(){let f=Fixture::new();write(&f.app.state.join("protected-snapshots.json"),"not json");assert!(snapshots::plan(&f.app,1).is_err());}

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
