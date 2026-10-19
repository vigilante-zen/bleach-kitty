function fish_right_prompt --description "Character-colored Git and command status"
    set -l last_status $status
    set -l duration "$CMD_DURATION"
    if not set -q KITTY_WINDOW_ID
        return 0
    end
    set -l accent 65C9FF
    if set -q bankai_prompt_secondary
        set accent "$bankai_prompt_secondary"
    end
    set -l separator ''
    if command -q git
        set -l branch (command git symbolic-ref --quiet --short HEAD 2>/dev/null)
        if test -z "$branch"
            set branch (command git rev-parse --short HEAD 2>/dev/null)
        end
        if test -n "$branch"
            set_color $accent
            printf 'git:%s' (string sub -l 28 -- "$branch")
            set separator ' · '
        end
    end
    if test $last_status -ne 0
        set_color FF6270
        printf '%sexit %s' "$separator" "$last_status"
        set separator ' · '
    end
    if string match -qr '^[0-9]+$' -- "$duration"; and test "$duration" -ge 1000
        set_color A6B3C8
        printf '%s%ss' "$separator" (math --scale=1 "$duration / 1000")
    end
    set_color normal
    return 0
end
