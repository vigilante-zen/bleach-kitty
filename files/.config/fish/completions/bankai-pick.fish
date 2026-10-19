complete -c bankai-pick -f
complete -c bankai-pick -l list -d 'List available portraits'
complete -c bankai-pick -l session -s s -d 'Choose only for this shell'
complete -c bankai-pick -n '__fish_seen_argument -l session -s s' -a reset -d 'Follow saved portrait settings'
complete -c bankai-pick -a '(bankai-pick --list)' -d 'Greeting portrait'
