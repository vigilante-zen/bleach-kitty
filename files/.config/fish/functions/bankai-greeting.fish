function bankai-greeting --description "Random Bleach portrait and system greeting"
    set -l replay_name
    set -l replay_art
    if test "$argv[1]" = --replay
        if test (count $argv) -ne 3; or not string match -qr '^[a-z0-9-]+$' -- "$argv[2]"; or not contains -- "$argv[3]" color manga
            printf 'Usage: bankai-greeting --replay <portrait> <color|manga>\n' >&2
            return 2
        end
        set replay_name "$argv[2]"
        set replay_art "$argv[3]"
        set -l folder portraits
        if test "$replay_art" = manga
            set folder manga
        end
        if not test -f "$HOME/.config/fastfetch/portraits/$replay_name.png"; or not test -f "$HOME/.config/fastfetch/$folder/$replay_name.png"
            printf 'Portrait edition is unavailable.\n' >&2
            return 1
        end
        set argv --compact
    else if test (count $argv) -gt 1; or begin; test (count $argv) -eq 1; and not contains -- "$argv[1]" --compact --full; end
        printf 'Usage: bankai-greeting [--compact|--full]\n' >&2
        return 2
    end
    set -l mode auto
    if test -f "$HOME/.config/fastfetch/greeting-mode"
        set -l saved_mode (string trim < "$HOME/.config/fastfetch/greeting-mode")
        if contains -- "$saved_mode" auto compact full off
            set mode "$saved_mode"
        end
    end
    switch "$argv[1]"
        case --compact
            set mode compact
        case --full
            set mode full
    end
    if test "$mode" = off
        return 0
    end
    set -l compact 0
    if set -q COLUMNS; and string match -qr '^[0-9]+$' -- "$COLUMNS"; and test "$COLUMNS" -lt 104
        set compact 1
    end
    if set -q LINES; and string match -qr '^[0-9]+$' -- "$LINES"; and test "$LINES" -lt 28
        set compact 1
    end
    switch "$mode"
        case compact
            set compact 1
        case full
            set compact 0
    end
    set -l config "$HOME/.config/fastfetch/soul-society-v5.jsonc"
    set -l portraits
    for portrait in "$HOME/.config/fastfetch/portraits/"*.png
        if test -f "$portrait"
            set -a portraits "$portrait"
        end
    end
    if set -q KITTY_WINDOW_ID; and test (count $portraits) -gt 0
        set -l portrait
        set -l choice_file "$HOME/.config/fastfetch/portrait-choice"
        set -l choice
        if test -n "$replay_name"
            set choice "$replay_name"
        else if set -q bankai_session_portrait
            set choice "$bankai_session_portrait"
        else if test -f "$choice_file"
            set choice (string trim < "$choice_file")
        end
        for candidate in $portraits
            if test "$candidate" = "$HOME/.config/fastfetch/portraits/$choice.png"
                set portrait "$candidate"
                break
            end
        end
        set -l state_dir "$HOME/.local/state/bleach"
        if set -q XDG_STATE_HOME; and test -n "$XDG_STATE_HOME"
            set state_dir "$XDG_STATE_HOME/bleach"
        end
        set -l last_file "$state_dir/last-portrait"
        set -l shuffled 0
        if test -z "$portrait"
            set portrait (command "$HOME/.local/bin/bankai-roster" next)
            or return $status
            set shuffled 1
        end
        set -l name (string replace -r '\.png$' '' -- (path basename "$portrait"))
        set -l canonical_portrait "$portrait"
        set -l art_mode color
        if test -f "$HOME/.config/fastfetch/portrait-art-mode"
            set art_mode (string trim < "$HOME/.config/fastfetch/portrait-art-mode")
        end
        if test -n "$replay_art"
            set art_mode "$replay_art"
        end
        set -l art_used color
        set -l manga "$HOME/.config/fastfetch/manga/$name.png"
        if test -f "$manga"
            if test "$art_mode" = manga
                set portrait "$manga"
                set art_used manga
            else if test "$art_mode" = mixed
                set art_used (random choice color manga)
                if test "$art_used" = manga
                    set portrait "$manga"
                end
            end
        end
        set -l themed_config "$HOME/.config/fastfetch/portrait-themes/$name.jsonc"
        if test -f "$themed_config"
            set config "$themed_config"
        end
        set -l logo_options --logo-width 28 --logo-height 14 --logo-position left
        if test $compact -eq 1
            set -l compact_config (string replace -r -- '\.jsonc$' '-compact.jsonc' "$config")
            if test -f "$compact_config"
                set config "$compact_config"
            end
            set logo_options --logo-width 20 --logo-height 10 --logo-position left
            if set -q COLUMNS; and string match -qr '^[0-9]+$' -- "$COLUMNS"; and test "$COLUMNS" -lt 90
                set logo_options --logo-width 16 --logo-height 8 --logo-position top
            end
            if set -q LINES; and string match -qr '^[0-9]+$' -- "$LINES"; and test "$LINES" -lt 24
                set logo_options --logo-width 12 --logo-height 6 --logo-position top
            end
        end
        command "$HOME/.local/bin/bankai-history-store" config "$config" "$art_used" | fastfetch --config - --logo "$portrait" --logo-type kitty $logo_options
        set -l render_pipeline $pipestatus
        set -l render_status $render_pipeline[-1]
        if test "$render_pipeline[1]" -ne 0
            return "$render_pipeline[1]"
        end
        if test $render_status -eq 0
            bankai-accent "$name"
            set -g bankai_portrait_art "$art_used"
            command "$HOME/.local/bin/bankai-history-store" record "$name" "$art_used"
            if test $shuffled -eq 0
                if mkdir -p "$state_dir" 2>/dev/null
                    printf '%s\n' "$canonical_portrait" > "$last_file" 2>/dev/null
                end
            end
        end
        return $render_status
    else
        if test $compact -eq 1
            set config "$HOME/.config/fastfetch/soul-society-v5-compact.jsonc"
        end
        fastfetch --config "$config"
    end
end
