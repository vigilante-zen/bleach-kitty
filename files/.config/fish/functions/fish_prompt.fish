function fish_prompt
    set -l last_status $status
    set -l primary E63946
    set -l secondary 65C9FF
    set -l label BANKAI
    if set -q bankai_prompt_primary bankai_prompt_secondary bankai_prompt_label
        set primary $bankai_prompt_primary
        set secondary $bankai_prompt_secondary
        set label $bankai_prompt_label
    end

    set_color $primary --bold
    printf "卍解 "

    set_color E8EDF5 --bold
    printf '%s ' "$label"

    set_color $secondary
    printf "%s\n" (prompt_pwd)

    if test $last_status -eq 0
        set_color $secondary
    else
        set_color E63946
    end

    printf "❯ "
    set_color normal
end
