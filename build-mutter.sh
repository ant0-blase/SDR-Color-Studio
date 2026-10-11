#!/usr/bin/env bash
# Download the latest official Arch Mutter packaging, patch and build locally.
# No automatic system installation and no unsupported GNOME major upgrades.
set -euo pipefail
PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ARCH_REPO="https://gitlab.archlinux.org/archlinux/packaging/packages/mutter.git"
PATCH="$PROJECT/patches/mutter-51-sdr-white-1624.patch"
OUT="$PROJECT/packages"
WORK="$PROJECT/work"

fail() { printf 'Erreur : %s\n' "$*" >&2; exit 1; }
(( EUID != 0 )) || fail 'Ne lance pas ce script en root : makepkg refuse root.'
for program in pacman git makepkg python3 patch gnome-shell; do
  command -v "$program" >/dev/null 2>&1 || fail "Programme manquant : $program (voir README)."
done
[[ -f "$PATCH" ]] || fail "Patch manquant : $PATCH"
[[ "$(gnome-shell --version)" =~ GNOME[[:space:]]Shell[[:space:]]51\. ]] ||
  fail 'Ce projet est validé seulement pour GNOME Shell 51.x.'

# A custom release suffix is deliberately ignored when comparing pkgver.
installed_full="$(pacman -Q mutter | awk '{print $2}')" || fail 'Mutter absent.'
installed_pkgver="${installed_full%%-*}"
[[ "$installed_pkgver" =~ ^51\.[0-9]+(\.[0-9]+)?$ ]] ||
  fail "Mutter installé ($installed_full) n'est pas en 51.x."

mkdir -p "$WORK" "$OUT"
BUILD="$(mktemp -d "$WORK/build-XXXXXXXX")"
printf 'Récupération de la dernière recette Mutter d’Arch Linux...\n'
git clone --quiet --depth=1 -- "$ARCH_REPO" "$BUILD/packaging" ||
  fail 'Clonage GitLab Arch impossible (vérifie la connexion).'
cd "$BUILD/packaging"

# PKGBUILD is executed by Bash, just as with makepkg. Trust only Arch's source.
read -r upstream_pkgver upstream_pkgrel < <(bash -c 'source ./PKGBUILD >/dev/null; printf "%s %s\n" "$pkgver" "$pkgrel"')
[[ "$upstream_pkgver" =~ ^51\.[0-9]+(\.[0-9]+)?$ ]] ||
  fail "La dernière version Arch ($upstream_pkgver) n'est pas en 51.x : mise à jour du patch nécessaire."
if [[ "$upstream_pkgver" != "$installed_pkgver" ]]; then
  fail "Arch a Mutter $upstream_pkgver, mais le système utilise $installed_pkgver. Effectue une mise à jour complète avec sudo pacman -Syu puis relance. Pas de mise à jour partielle."
fi
printf 'GNOME 51 détecté ; Mutter installé : %s ; source Arch : %s-%s.\n' \
  "$installed_full" "$upstream_pkgver" "$upstream_pkgrel"
cp -- "$PATCH" ./sdr-color-white-ceiling.patch
python3 "$PROJECT/scripts/inject-pkgbuild.py" ./PKGBUILD ./sdr-color-white-ceiling.patch
# This statically validates the recipe before source retrieval and compilation.
read -r patched_pkgver patched_pkgrel < <(bash -c 'source ./PKGBUILD >/dev/null; printf "%s %s\n" "$pkgver" "$pkgrel"')
[[ "$patched_pkgver" == "$upstream_pkgver" && "$patched_pkgrel" == "$upstream_pkgrel.9001" ]] ||
  fail 'PKGBUILD patché incohérent ; compilation annulée.'

printf 'Téléchargement des sources vérifiées et compilation avec makepkg...\n'
printf 'Dossier de travail : %s\n' "$BUILD"
makepkg -s --noconfirm

shopt -s nullglob
main=( ./mutter-"$upstream_pkgver"-"$patched_pkgrel"-*.pkg.tar.* )
optional=( ./mutter-devkit-"$upstream_pkgver"-"$patched_pkgrel"-*.pkg.tar.* )
(( ${#main[@]} == 1 )) || fail 'Paquet Mutter principal manquant ou ambigu.'
packages=( "${main[@]}" "${optional[@]}" )
cp -- "${packages[@]}" "$OUT/"
printf '%s\n' "$upstream_pkgver" > "$OUT/last-pkgver.txt"
printf '%s\n' "$patched_pkgrel" > "$OUT/last-pkgrel.txt"
printf '\nPaquet(s) construits, PAS installés :\n'
for item in "${packages[@]}"; do printf '  %s/%s\n' "$OUT" "${item#./}"; done
printf '\nAprès vérification, lance : ./install-patched-mutter.sh\n'
printf 'Les nouvelles versions Mutter 51.x seront récupérées lors du prochain build ; les versions incompatibles seront refusées.\n'
