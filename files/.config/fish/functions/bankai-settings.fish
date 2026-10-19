function bankai-settings --description "Bleach Kitty settings menu"
    if test (count $argv) -gt 0
        if test (count $argv) -eq 1; and contains -- "$argv[1]" --help -h
            printf 'Run bankai-settings in Kitty to manage portraits, groups, favorites, greeting layout and backups.\n'
            return 0
        end
        printf 'Usage: bankai-settings [--help]\n' >&2
        return 2
    end
    if not isatty stdin
        command "$HOME/.local/bin/bankai-roster" status
        bankai-layout
        printf '\nOpen Kitty and run bankai-settings for the menu.\n'
        return 0
    end
    if not command -q fzf
        printf 'bankai-settings needs fzf. Use bankai-pick, bankai-group, bankai-favorites, bankai-layout or bankai-backup directly.\n' >&2
        return 1
    end
    while true
        set -l mode auto
        if test -f "$HOME/.config/fastfetch/greeting-mode"
            set mode (string trim < "$HOME/.config/fastfetch/greeting-mode")
        end
        set -l selection shuffle
        if test -f "$HOME/.config/fastfetch/portrait-choice"
            set -l saved (string trim < "$HOME/.config/fastfetch/portrait-choice")
            if test "$saved" != random; and test -f "$HOME/.config/fastfetch/portraits/$saved.png"
                set selection "$saved"
            end
        end
        if set -q bankai_session_portrait
            set selection "$bankai_session_portrait (this shell)"
        end
        set -l status_lines (command "$HOME/.local/bin/bankai-roster" status)
        set -l rotation (string join ' · ' -- $status_lines[1..3])
        set -l art color
        if test -f "$HOME/.config/fastfetch/portrait-art-mode"
            set art (string trim < "$HOME/.config/fastfetch/portrait-art-mode")
        end
        set -l header "Portrait: $selection · Greeting: $mode · Art: $art
$rotation
Enter opens · Esc exits"
        set -l items 'Choose portrait' 'Portrait art' 'Recent art' 'Character groups' 'Edit favorites' 'Use saved favorites' 'Rotate everyone' 'Shuffle style' 'Greeting layout' 'Preview greeting' 'Check setup' Backups
        if set -q bankai_portrait; and test -f "$HOME/.config/fastfetch/portraits/$bankai_portrait.png"
            set -l favorites (command "$HOME/.local/bin/bankai-roster" list)
            if contains -- "$bankai_portrait" $favorites
                set -a items 'Remove current favorite'
            else
                set -a items 'Favorite current portrait'
            end
        end
        set -a items Exit
        set -l action (printf '%s\n' $items | fzf --prompt='BANKAI settings > ' --header="$header" --height=80% --layout=reverse --border=rounded --color='fg:#E8EDF5,bg:#090C12,hl:#65C9FF,fg+:#FFFFFF,bg+:#202838,hl+:#65C9FF,pointer:#E63946,prompt:#E63946')
        or return 0
        switch "$action"
            case 'Choose portrait'
                bankai-pick
            case 'Portrait art'
                set -l art_info (bankai-art)
                set -l coverage (string match 'Manga available:*' -- $art_info)
                set -l art_style (printf '%s\n' color manga mixed | fzf --prompt='Portrait art > ' --height=12 --layout=reverse --header="$coverage · Mixed alternates editions · Esc returns")
                if test $status -eq 0; and test -n "$art_style"
                    bankai-art "$art_style"
                end
            case 'Recent art'
                bankai-history
                return $status
            case 'Character groups'
                set -l group (command "$HOME/.local/bin/bankai-roster" groups | fzf --prompt='Character group > ' --height=14 --layout=reverse --header='Enter selects · Esc returns')
                if test $status -eq 0; and test -n "$group"
                    bankai-group "$group"
                end
            case 'Edit favorites'
                bankai-favorites
            case 'Favorite current portrait' 'Remove current favorite'
                bankai-favorites toggle
            case 'Use saved favorites'
                bankai-favorites use
            case 'Rotate everyone'
                bankai-group all
            case 'Shuffle style'
                set -l style (printf '%s\n' portrait character | fzf --prompt='Shuffle style > ' --height=12 --layout=reverse --header='portrait: every image once · character: equal character turns')
                if test $status -eq 0; and test -n "$style"
                    bankai-shuffle "$style"
                end
            case 'Greeting layout'
                set -l layout (printf '%s\n' auto compact full off | fzf --prompt='Greeting layout > ' --height=12 --layout=reverse --header='Saves for future greetings · Esc returns')
                if test $status -eq 0; and test -n "$layout"
                    bankai-layout "$layout"
                end
            case 'Preview greeting'
                bankai-greeting --compact
                return $status
            case 'Check setup'
                bankai-doctor
                return $status
            case Backups
                set -l operation (printf '%s\n' 'Create snapshot' 'Verify snapshot' 'Restore snapshot' Back | fzf --prompt='Theme backups > ' --height=12 --layout=reverse --header='Restore saves current settings first · Esc returns')
                if test $status -ne 0
                    continue
                end
                switch "$operation"
                    case 'Create snapshot'
                        bankai-backup
                    case 'Verify snapshot' 'Restore snapshot'
                        set -l snapshots (command "$HOME/.local/bin/bankai-backup" list)
                        if test (count $snapshots) -eq 0
                            printf 'No snapshots yet. Choose Create snapshot first.\n'
                            continue
                        end
                        set -l name (printf '%s\n' $snapshots | fzf --prompt="$operation > " --height=60% --layout=reverse --header='Enter selects snapshot · Esc returns')
                        if test $status -eq 0; and test -n "$name"
                            if test "$operation" = 'Verify snapshot'
                                bankai-backup verify "$name"
                            else
                                bankai-backup restore "$name"
                                return $status
                            end
                        end
                end
            case Exit
                return 0
        end
    end
end
