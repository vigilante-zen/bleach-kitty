function bankai-manga-preview --description "Preview Urahara's manga edition without changing rotation"
    if test (count $argv) -gt 0
        if test (count $argv) -eq 1; and contains -- "$argv[1]" --help -h
            printf 'Run in Kitty to preview a manga-style Urahara greeting. Saved portraits, favorites, shuffle and shell accents stay unchanged.\n'
            return 0
        end
        printf 'Usage: bankai-manga-preview\n' >&2
        return 2
    end
    if not set -q KITTY_WINDOW_ID
        printf 'Open Kitty and run bankai-manga-preview.\n' >&2
        return 1
    end
    set -l image "$HOME/.config/fastfetch/previews/urahara-manga.png"
    if not test -f "$image"
        printf 'Manga preview image is unavailable.\n' >&2
        return 1
    end
    fastfetch --config "$HOME/.config/fastfetch/portrait-themes/urahara-compact.jsonc" --logo "$image" --logo-type kitty --logo-width 20 --logo-height 10 --logo-position auto
end
