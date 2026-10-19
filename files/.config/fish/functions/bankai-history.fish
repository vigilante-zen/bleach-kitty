function bankai-history --description 'Browse and replay recent Bleach art editions'
    if test (count $argv) -gt 1
        printf 'Usage: bankai-history [list|number]\n' >&2
        return 2
    end
    set -l entry $argv[1]
    if test "$entry" = --help; or test "$entry" = -h
        printf 'bankai-history: browse recent art in Kitty.\nbankai-history list: print recent editions.\nbankai-history <number>: show that exact edition once, preserving saved settings and shuffle position.\n'
        return 0
    end
    if test -z "$entry"; or test "$entry" = list
        set -l rows (command "$HOME/.local/bin/bankai-history-store" list)
        or return $status
        if test (count $rows) -eq 0
            printf 'No art history yet. New greetings will appear here.\n'
            return 0
        end
        if test "$entry" = list; or not isatty stdin; or not command -q fzf
            for row in $rows
                set -l fields (string split \t -- "$row")
                printf '%s  %s\n' "$fields[1]" "$fields[4]"
            end
            return 0
        end
        set -l selected (printf '%s\n' $rows | fzf --delimiter='\t' --with-nth=4 --prompt='Recent art > ' --header='Newest first · Enter shows exact edition once · Esc returns' --layout=reverse --height=80% --preview='"$HOME/.local/bin/bankai-preview" {2} {3}' --preview-window='right,60%,<80(up,65%)')
        or return 0
        set entry (string split \t -- "$selected")[1]
    end
    if not string match -qr '^[1-9][0-9]*$' -- "$entry"
        printf 'Usage: bankai-history [list|number]\n' >&2
        return 2
    end
    if not set -q KITTY_WINDOW_ID
        printf 'Open Kitty to replay an art edition. Use bankai-history list to browse.\n' >&2
        return 1
    end
    set -l record (command "$HOME/.local/bin/bankai-history-store" get "$entry")
    or return $status
    bankai-greeting --replay "$record[1]" "$record[2]"
end
