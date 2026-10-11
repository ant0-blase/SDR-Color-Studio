#!/usr/bin/env bash
set -euo pipefail
if (( EUID == 0 )); then echo 'Ne lance pas ce script avec sudo.' >&2; exit 1; fi
if ! command -v gnome-shell >/dev/null || ! gnome-shell --version | grep -Eq 'GNOME Shell 51\.'; then
  echo 'Ce kit est prévu pour GNOME Shell 51 (session Wayland conseillée).' >&2; exit 1
fi
for dep in glib-compile-schemas gnome-extensions gdctl python3; do
  command -v "$dep" >/dev/null || { echo "Outil manquant : $dep" >&2; exit 1; }
done
python3 - <<'PY'
try:
 import gi
 gi.require_version('Gtk','4.0')
 gi.require_version('Adw','1')
 from gi.repository import Gtk, Adw
except (ImportError,ValueError) as e:
 raise SystemExit(f'Dépendances manquantes : {e}\nInstalle : sudo pacman -S --needed python-gobject gtk4 libadwaita')
PY
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXT="$HOME/.local/share/gnome-shell/extensions/sdr-color-studio@local"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
DATA="$HOME/.local/share/sdr-color-studio"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$EXT/schemas" "$BIN" "$APPS" "$DATA" "$ICONS"
install -m 644 "$ROOT/extension/metadata.json" "$EXT/metadata.json"
install -m 644 "$ROOT/extension/extension.js" "$EXT/extension.js"
install -m 644 "$ROOT/extension/prefs.js" "$EXT/prefs.js"
install -m 644 "$ROOT/extension/i18n.json" "$EXT/i18n.json"
install -m 644 "$ROOT/extension/schemas/org.gnome.shell.extensions.sdr-color-studio.gschema.xml" "$EXT/schemas/"
glib-compile-schemas "$EXT/schemas"
install -m 755 "$ROOT/app/studio.py" "$BIN/sdr-color-studio"
install -m 755 "$ROOT/app/hdr10_patterns.py" "$BIN/sdr-color-studio-hdr-test"
install -m 644 "$ROOT/assets/hdr10-reference-steps.mp4" "$DATA/hdr10-reference-steps.mp4"
install -m 644 "$ROOT/assets/logo.svg" "$ICONS/io.github.sdrcolor.Studio.svg"
cat > "$APPS/io.github.sdrcolor.Studio.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=SDR Color Studio
Comment=GNOME 51 HDR white / saturation / contraste
Exec=$BIN/sdr-color-studio
Icon=io.github.sdrcolor.Studio
Terminal=false
Categories=Settings;DesktopSettings;
StartupNotify=true
EOF
if ! gnome-extensions enable 'sdr-color-studio@local'; then
  echo 'L’extension n’est pas encore connue de GNOME Shell : déconnecte-toi/reconnecte-toi, puis exécute :' >&2
  echo '  gnome-extensions enable sdr-color-studio@local' >&2
fi
printf '\nInstallation terminée. Préférences intégrées :\n  gnome-extensions prefs sdr-color-studio@local\nGUI indépendante :\n  %s/sdr-color-studio\n' "$BIN"
printf 'Si la couleur ne change pas, déconnexion/reconnexion GNOME et : gnome-extensions info sdr-color-studio@local\n'
printf 'Le patch Mutter est OPTIONNEL : ./build-mutter.sh\n'
