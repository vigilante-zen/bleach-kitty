function fish_title --description "Bleach character and current task in Kitty titles"
    set -l location (prompt_pwd -d 1 -D 1)
    set -l parts
    if set -q KITTY_WINDOW_ID
        set -l label BANKAI
        if set -q bankai_prompt_label
            set label "$bankai_prompt_label"
        end
        set -a parts "$label"
    end
    if set -q SSH_TTY
        set -a parts '['(prompt_hostname | string sub -l 10)']'
    end
    if set -q argv[1]; and test -n "$argv[1]"; and test "$argv[1]" != fish
        set -a parts (string sub -l 24 -- "$argv[1]")
    end
    set -a parts "$location"
    set -l title (string join ' · ' -- $parts)
    string replace -ar '[\x00-\x1f\x7f]' '' -- "$title"
    return 0
end
