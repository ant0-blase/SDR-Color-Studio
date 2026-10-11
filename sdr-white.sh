#!/usr/bin/env bash
set -euo pipefail
if ! command -v gdctl >/dev/null 2>&1; then
  echo 'gdctl est requis (Mutter/GNOME 51).' >&2; exit 1
fi
MONITOR="${SDR_WHITE_MONITOR:-}"
if [[ ${1:-} == '--monitor' ]]; then
  MONITOR="${2:?Connecteur manquant}"
  shift 2
fi
if [[ $# != 1 || ! "$1" =~ ^[0-9]+$ ]]; then
  echo "Usage: $(basename "$0") [--monitor DP-1] NITS" >&2; exit 2
fi
if [[ -z "$MONITOR" ]]; then
  MONITOR="$(gdctl show | grep -m1 -oE 'Monitor [[:alnum:]_.-]+ \(' | sed -E 's/^Monitor ([^ ]+) \($/\1/' || true)"
fi
[[ -n "$MONITOR" ]] || { echo 'Aucun moniteur détecté. Utilise --monitor.' >&2; exit 1; }
nits=$1
if (( nits < 21 || nits > 1624 )); then
  echo 'Plage nominale permise par le patch : 21–1624 nits demandés.' >&2
  exit 2
fi
v=$(( (nits * 100 + 101) / 203 ))
# gdctl still performs validation and will reject unsupported/unpatched ranges.
printf 'Moniteur %s: blanc SDR nominal demandé %s nits (gdctl %d).\n' "$MONITOR" "$nits" "$v"
gdctl prefs --monitor "$MONITOR" --backlight "$v"
