fn main() {
    let mut build = cc::Build::new();
    build.cpp(true).file("native/gui.cpp").flag("-std=c++17").flag("-fPIC");
    for module in ["Qt6Widgets", "Qt6Svg", "Qt6Network"] {
        let library = pkg_config::Config::new().probe(module).expect("Qt 6 development files are required");
        for include in library.include_paths {
            build.include(include);
        }
    }
    build.compile("bankai_qt");
    println!("cargo:rerun-if-changed=native/gui.cpp");
}
