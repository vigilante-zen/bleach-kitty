function bankai-art --description "Choose color, manga or mixed greeting portraits"
    set -l file "$HOME/.config/fastfetch/portrait-art-mode"
    if test (count $argv) -eq 0
        set -l mode color
        if test -f "$file"
            set -l saved (string trim < "$file")
            if contains -- "$saved" color manga mixed
                set mode "$saved"
            end
        end
        set -l coverage 0
        set -l total 0
        for portrait in "$HOME/.config/fastfetch/portraits/"*.png
            if test -f "$portrait"
                set total (math "$total + 1")
                if test -f "$HOME/.config/fastfetch/manga/"(path basename "$portrait")
                    set coverage (math "$coverage + 1")
                end
            end
        end
        printf 'Portrait art: %s\nManga available: %s/%s portraits\nColor art fills in where manga is unavailable.\n' "$mode" "$coverage" "$total"
        return 0
    end
    if test (count $argv) -ne 1
        printf 'Usage: bankai-art color|manga|mixed\n' >&2
        return 2
    end
    if not contains -- "$argv[1]" color manga mixed
        printf 'Usage: bankai-art color|manga|mixed\n' >&2
        return 2
    end
    printf '%s\n' "$argv[1]" > "$file"
    or return 1
    printf 'Portrait art: %s (applies at the next greeting)\n' "$argv[1]"
end
