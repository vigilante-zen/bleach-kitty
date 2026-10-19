complete -c bankai-backup -f
complete -c bankai-backup -n '__fish_use_subcommand' -a 'create list verify restore'
complete -c bankai-backup -n '__fish_seen_subcommand_from verify restore' -a '(command "$HOME/.local/bin/bankai-backup" list)'
