
var ps = panels();
for (var i = 0; i < ps.length; ++i) {
    var p = ps[i];
    p.floating = true;
    p.opacity = "translucent";
    p.height = 44;
    var widgets = p.widgets();
    for (var j = 0; j < widgets.length; ++j) {
        var w = widgets[j];
        if (w.type === "org.kde.plasma.icontasks" || w.type === "org.kde.plasma.taskmanager") {
            w.currentConfigGroup = ["General"];
            var old = w.readConfig("launchers", []);
            if (typeof old === "string") old = old.split(",");
            var keep = [];
            for (var k = 0; k < old.length; ++k) {
                if (!/ghostty|Alacritty|kitty\.desktop|bleach-terminal|bleach-monitor/i.test(old[k])) keep.push(old[k]);
            }
            keep.push("applications:bleach-terminal.desktop");
            keep.push("applications:bleach-monitor.desktop");
            w.writeConfig("launchers", keep);
        }
    }
}
