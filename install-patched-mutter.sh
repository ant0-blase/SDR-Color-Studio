#!/usr/bin/env bash
# Explicit opt-in: no compositor replacement during build or GUI installation.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
(( EUID != 0 )) || { echo 'Lance sans sudo.' >&2; exit 1; }
[[ -f "$ROOT/packages/last-pkgver.txt" && -f "$ROOT/packages/last-pkgrel.txt" ]] || {
  echo 'Aucune compilation détectée. Lance ./build-mutter.sh' >&2; exit 1; }
pkgver="$(cat "$ROOT/packages/last-pkgver.txt")"
pkgrel="$(cat "$ROOT/packages/last-pkgrel.txt")"
current="$(pacman -Q mutter | awk '{print $2}')"
[[ "${current%%-*}" == "$pkgver" ]] || {
  echo "La version installée de Mutter ($current) est différente du build ($pkgver). Recompile d’abord." >&2
  exit 1
}
shopt -s nullglob
main=( "$ROOT"/packages/mutter-"$pkgver"-"$pkgrel"-*.pkg.tar.* )
(( ${#main[@]} == 1 )) || { echo 'Paquet Mutter manquant ou ambigu.' >&2; exit 1; }
args=( "${main[0]}" )
if pacman -Qq mutter-devkit >/dev/null 2>&1; then
  devkit=( "$ROOT"/packages/mutter-devkit-"$pkgver"-"$pkgrel"-*.pkg.tar.* )
  (( ${#devkit[@]} == 1 )) || { echo 'mutter-devkit installé mais son paquet patché est absent.' >&2; exit 1; }
  args+=( "${devkit[0]}" )
fi
printf 'Remplacement de Mutter %s par une compilation locale non signée.\n' "$current"
printf 'Si GNOME ne démarre plus : Ctrl+Alt+F3, puis sudo pacman -S mutter.\n'
read -r -p 'Installer le(s) paquet(s) compilé(s) ? [o/N] ' reply
[[ "$reply" == [oOyY] ]] || exit 0
sudo pacman -U -- "${args[@]}"
echo 'Redémarre ta session pour charger Mutter. Aucun redémarrage automatique.'
