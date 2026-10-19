function bankai-layout --description "Save the Kitty greeting layout"
    set -l file "$HOME/.config/fastfetch/greeting-mode"
    if test (count $argv) -eq 0
        set -l mode auto
        if test -f "$file"
            set mode (string trim < "$file")
        end
        printf 'Greeting: %s\nChoose: bankai-layout auto|compact|full|off\n' "$mode"
        return 0
    end
    if test (count $argv) -gt 1
        printf 'Usage: bankai-layout auto|compact|full|off\n' >&2
        return 2
    end
    if not contains -- "$argv[1]" auto compact full off
        printf 'Usage: bankai-layout auto|compact|full|off\n' >&2
        return 2
    end
    printf '%s\n' "$argv[1]" > "$file"
    or return 1
    printf 'Greeting: %s (applies at the next greeting)\n' "$argv[1]"
end
