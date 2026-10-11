#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 ]]; then
  echo 'Lance ce script sans sudo : il appellera sudo lui-meme.' >&2
  exit 1
fi
printf 'Rétablissement du Mutter officiel depuis les dépôts Arch.\n'
printf 'Les dépôts doivent être synchronisés avec le reste de GNOME.\n'
read -r -p 'Restaurer le Mutter officiel ? [o/N] ' answer
if [[ "$answer" != [oOyY] ]]; then exit 0; fi
sudo pacman -S mutter
printf 'Déconnecte-toi puis reconnecte-toi (ou redémarre) pour charger le Mutter officiel.\n'
