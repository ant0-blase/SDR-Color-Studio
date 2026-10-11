#!/usr/bin/env bash
set -euo pipefail
if (( EUID == 0 )); then echo 'Ne lance pas comme root.' >&2; exit 1; fi
gnome-extensions disable 'sdr-color-studio@local' 2>/dev/null || true
rm -rf -- "$HOME/.local/share/gnome-shell/extensions/sdr-color-studio@local"
rm -f -- "$HOME/.local/bin/sdr-color-studio" "$HOME/.local/bin/sdr-color-studio-hdr-test" "$HOME/.local/share/applications/io.github.sdrcolor.Studio.desktop"
rm -f -- "$HOME/.local/share/sdr-color-studio/hdr10-reference-steps.mp4"
rm -f -- "$HOME/.local/share/icons/hicolor/scalable/apps/io.github.sdrcolor.Studio.svg"
rmdir -- "$HOME/.local/share/sdr-color-studio" 2>/dev/null || true
echo 'Extension et GUI supprimées. Les paramètres GSettings restent stockés (pas de destruction des préférences).'
echo 'Si tu as installé Mutter modifié, restaure séparément : ./restore-official.sh'
