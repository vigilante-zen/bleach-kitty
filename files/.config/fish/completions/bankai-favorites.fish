complete -c bankai-favorites -f
complete -c bankai-favorites -n '__fish_use_subcommand' -a 'add remove toggle use all list status clear'
complete -c bankai-favorites -n '__fish_seen_subcommand_from add remove toggle' -a '(bankai-pick --list | string match -v random)'
