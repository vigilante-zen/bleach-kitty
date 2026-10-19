function bankai-pick --description "Choose a Bleach greeting portrait or random mode"
    argparse -n bankai-pick s/session l/list -- $argv
    or return $status
    set -l choices random
    for portrait in "$HOME/.config/fastfetch/portraits/"*.png
        if test -f "$portrait"
            set -a choices (string replace -r '\.png$' '' -- (path basename "$portrait"))
        end
    end
    if set -q _flag_session
        set -a choices reset
    end
    if test (count $argv) -gt 1
        printf 'Usage: bankai-pick [--session] [--list|random|portrait-name|reset]\n' >&2
        return 2
    end
    if set -q _flag_list
        if test (count $argv) -gt 0
            printf 'Use --list without a portrait name.\n' >&2
            return 2
        end
        printf '%s\n' $choices
        return 0
    end
    set -l choice $argv
    if test (count $choice) -eq 0
        if not isatty stdin; or not command -q fzf
            printf 'Choose with: bankai-pick <name>\nAvailable portraits:\n'
            printf '  %s\n' $choices
            return 0
        end
        set -l picker_options --height=12
        if set -q KITTY_WINDOW_ID; and test -x "$HOME/.local/bin/bankai-preview"
            set picker_options --height=80% --preview='"$HOME/.local/bin/bankai-preview" {1}' --preview-window='right,60%,border-left,<80(up,65%,border-bottom)'
        end
        set -l records (command "$HOME/.local/bin/bankai-roster" catalog)
        or return $status
        set -l scope 'Saved default for future tabs'
        if set -q _flag_session
            set scope 'This shell only'
            set -p records 'reset'(printf '\t')'Use saved defaults'
        end
        set -l selected (begin; printf 'random\tShuffle current pool\n'; printf '%s\n' $records; end | fzf --delimiter='\t' --with-nth=2.. --prompt='BANKAI portrait > ' --header="$scope · Enter selects · Esc cancels" --layout=reverse --bind='ctrl-/:toggle-preview' $picker_options)
        or return 0
        set -l fields (string split -m 1 \t -- "$selected")
        set choice "$fields[1]"
    end
    if not contains -- "$choice" $choices
        printf 'Unknown portrait: %s. Run bankai-pick --list.\n' "$choice" >&2
        return 2
    end
    if set -q _flag_session
        if test "$choice" = reset
            set -e -g bankai_session_portrait
            printf 'This shell follows saved portrait settings.\n'
        else
            set -g bankai_session_portrait "$choice"
            printf 'This shell portrait: %s\n' "$choice"
        end
    else
        printf '%s\n' "$choice" > "$HOME/.config/fastfetch/portrait-choice"
        or return 1
        set -e -g bankai_session_portrait
        printf 'Greeting portrait: %s\n' "$choice"
    end
    if set -q KITTY_WINDOW_ID
        bankai-greeting
    end
end
