function bankai-monitor-v5 --description "BLEACH V5 live Reiatsu monitor"
    set -l config "$HOME/.config/btop/bleach-v5/btop.conf"
    set -l portrait
    if set -q bankai_portrait
        set portrait "$bankai_portrait"
    else if test -f "$HOME/.config/fastfetch/portrait-choice"
        set portrait (string trim < "$HOME/.config/fastfetch/portrait-choice")
    end
    if string match -qr '^[a-z0-9-]+$' -- "$portrait"
        set -l themed_config "$HOME/.config/btop/portraits/$portrait.conf"
        if test -f "$themed_config"
            set config "$themed_config"
        end
    end
    btop --config "$config" $argv
end
