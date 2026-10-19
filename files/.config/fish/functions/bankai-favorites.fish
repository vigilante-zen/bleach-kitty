function bankai-favorites --description "Manage the Bleach favorites rotation"
    set -l helper "$HOME/.local/bin/bankai-roster"
    if test (count $argv) -gt 0
        switch "$argv[1]"
            case toggle
                if test (count $argv) -eq 1
                    if not set -q bankai_portrait; or not test -f "$HOME/.config/fastfetch/portraits/$bankai_portrait.png"
                        printf 'No active portrait in this shell. Run a greeting, or use bankai-favorites toggle <name>.\n' >&2
                        return 2
                    end
                    command "$helper" toggle "$bankai_portrait"
                else
                    command "$helper" $argv
                end
                return $status
            case add remove use all list status clear
                command "$helper" $argv
                return $status
            case '*'
                printf 'Usage: bankai-favorites [add|remove <names>...|toggle [name]|use|all|list|status|clear]\n' >&2
                return 2
        end
    end
    if not isatty stdin; or not command -q fzf
        command "$helper" status
        printf '\nUse bankai-favorites add <names> or bankai-favorites all.\n'
        return
    end
    set -l choices (command "$helper" catalog)
    or return $status
    set -l saved (command "$helper" list)
    set -l initial_actions
    set -l index 1
    for record in $choices
        set -l fields (string split -m 1 \t -- "$record")
        if contains -- "$fields[1]" $saved
            set -a initial_actions "pos($index)" select
        end
        set index (math "$index + 1")
    end
    set -a initial_actions first
    set -l initialize (string join + -- $initial_actions)
    set -l options --height=80%
    if set -q KITTY_WINDOW_ID; and test -x "$HOME/.local/bin/bankai-preview"
        set -a options --preview='"$HOME/.local/bin/bankai-preview" {1}' --preview-window='right,60%,border-left,<80(up,65%,border-bottom)'
    end
    set -l selected (printf '%s\n' $choices | fzf --multi --sync --delimiter='\t' --with-nth=2.. --with-shell='sh -c' --prompt='BANKAI favorites > ' --header='Tab toggles · Alt-A all · Alt-D none · Enter saves marked · Esc cancels' --layout=reverse --bind="load:$initialize" --bind='alt-a:select-all,alt-d:deselect-all' --bind='enter:transform:if test "$FZF_SELECT_COUNT" -eq 0; then echo "print(__BANKAI_CLEAR__)+accept"; else echo accept; fi' $options)
    set -l picker_status $status
    if contains -- __BANKAI_CLEAR__ $selected
        command "$helper" clear
        return $status
    end
    if test $picker_status -ne 0
        return 0
    end
    if test (count $selected) -gt 0
        set -l names
        for record in $selected
            set -l fields (string split -m 1 \t -- "$record")
            set -a names "$fields[1]"
        end
        command "$helper" set $names
    end
end
