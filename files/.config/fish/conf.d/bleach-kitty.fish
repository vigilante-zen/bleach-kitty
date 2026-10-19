# Bleach Kitty startup. No distribution-specific configuration required.
if status is-interactive; and set -q KITTY_WINDOW_ID
    fish_add_path "$HOME/.local/bin"
    bankai-syntax E63946 65C9FF
    function fish_greeting
        bankai-greeting
    end
end
