#!/usr/bin/env python3
"""Append a tightly-scoped Mutter 51 patch to Arch's current PKGBUILD.

Never rewrites Arch's original prepare()/package() logic. A wrapper calls
prepare() first, checks an exact source anchor, then applies a strict patch.
"""
import hashlib
import pathlib
import sys

DIGESTS = {
    'b2sums': lambda b: hashlib.blake2b(b, digest_size=64).hexdigest(),
    'sha256sums': lambda b: hashlib.sha256(b).hexdigest(),
    'sha512sums': lambda b: hashlib.sha512(b).hexdigest(),
    'sha224sums': lambda b: hashlib.sha224(b).hexdigest(),
    'sha384sums': lambda b: hashlib.sha384(b).hexdigest(),
    'sha1sums': lambda b: hashlib.sha1(b).hexdigest(),
    'md5sums': lambda b: hashlib.md5(b).hexdigest(),
}


def inject(recipe: pathlib.Path, patch: pathlib.Path) -> None:
    if not recipe.is_file() or not patch.is_file():
        raise SystemExit('PKGBUILD ou patch introuvable')
    if 'sdr_color_upstream_prepare' in recipe.read_text():
        raise SystemExit('PKGBUILD déjà modifié : refus de réinjecter le patch')
    b = patch.read_bytes()
    content = """

# SDR Color Studio downstream patch — fetched from official Arch packaging.
# The suffix distinguishes this build from the signed official Arch package.
pkgrel="${pkgrel}.9001"
source+=("sdr-color-white-ceiling.patch")
"""
    for var, func in DIGESTS.items():
        content += f"""if declare -p {var} >/dev/null 2>&1; then
  {var}+=("{func(b)}")
fi
"""
    content += r"""
# Preserve Arch's existing preparation steps, including any vendor patches.
if declare -F prepare >/dev/null 2>&1; then
  eval "$(declare -f prepare | sed '1s/^prepare /sdr_color_upstream_prepare /')"
fi
prepare() {
  if declare -F sdr_color_upstream_prepare >/dev/null 2>&1; then
    sdr_color_upstream_prepare
  fi
  local target source_root
  target="$(find "$srcdir" -type f -path '*/src/backends/meta-backlight-ref-white.c' -print -quit)"
  [[ -n "$target" ]] || { echo 'Mutter source file missing; patch refused.' >&2; return 1; }
  grep -Fq '"brightness-max", 210,' "$target" || {
    echo 'Mutter no longer has the expected 210 ceiling; patch refused.' >&2
    return 1
  }
  source_root="${target%/src/backends/meta-backlight-ref-white.c}"
  patch --batch --forward --fuzz=0 --dry-run -p1 -d "$source_root" \
    -i "$srcdir/sdr-color-white-ceiling.patch" || {
    echo 'Mutter source changed; refusing an incompatible patch.' >&2
    return 1
  }
  patch --batch --forward --fuzz=0 -p1 -d "$source_root" \
    -i "$srcdir/sdr-color-white-ceiling.patch"
}
"""
    recipe.write_text(recipe.read_text() + content, encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: inject-pkgbuild.py PKGBUILD patch-file')
    inject(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
