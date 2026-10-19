function bankai-syntax --description "Apply Bleach colors to Fish command highlighting"
    if not set -q KITTY_WINDOW_ID
        return 0
    end
    if test (count $argv) -ne 2
        return 2
    end
    for color in $argv
        if not string match -qr '^[A-Fa-f0-9]{6}$' -- "$color"
            return 2
        end
    end
    set -l primary "$argv[1]"
    set -l secondary "$argv[2]"
    set -g fish_color_normal E8EDF5
    set -g fish_color_command $secondary
    set -g fish_color_keyword $primary --bold
    set -g fish_color_quote F0C674
    set -g fish_color_redirection $secondary
    set -g fish_color_param E8EDF5
    set -g fish_color_option $secondary
    set -g fish_color_comment 8190A6
    set -g fish_color_autosuggestion 74839A
    set -g fish_color_valid_path --underline
    set -g fish_color_operator $primary
    set -g fish_color_escape $secondary
    set -g fish_color_end $primary
    set -g fish_color_error FF6270
    set -g fish_color_selection E8EDF5 --background=24445B
    set -g fish_color_search_match 090C12 --background=$secondary
    set -g fish_color_history_current $secondary --bold
    set -g fish_pager_color_prefix $secondary --bold
    set -g fish_pager_color_completion E8EDF5
    set -g fish_pager_color_description A6B3C8
    set -g fish_pager_color_progress $secondary --bold
    set -g fish_pager_color_selected_background --background=24445B
    if status is-interactive; and isatty stdout
        # Kitty's OSC 12 sets the cursor color for this terminal window.
        printf '\e]12;#%s\a' "$primary"
    end
    return 0
end
