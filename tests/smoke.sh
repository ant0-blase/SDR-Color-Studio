#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
for file in "$root"/*.sh; do bash -n "$file"; done
python3 -B - <<'PY_CODE' "$root"
import ast, json, pathlib, sys, tempfile, xml.etree.ElementTree as ET
r=pathlib.Path(sys.argv[1])
for py in list(r.glob('app/*.py')) + list(r.glob('scripts/*.py')):
    ast.parse(py.read_text(), filename=str(py))
json.loads((r/'extension/metadata.json').read_text())
xml=ET.parse(r/'extension/schemas/org.gnome.shell.extensions.sdr-color-studio.gschema.xml')
keys={x.attrib['name'] for x in xml.findall('.//key')}
assert keys == {'enabled', 'monitor-profiles', 'protect-fullscreen', 'language'}
translations=json.loads((r/'extension/i18n.json').read_text())
assert {'en','de','es','it','pt_BR'} <= translations.keys()
assert translations['en']['Écran']=='Display'
assert (r/'assets/screenshots/preferences-fr.png').is_file()
assert (r/'assets/logo.svg').is_file()
assert (r/'extension/prefs.js').exists(), 'GNOME Extensions requires prefs.js'
assert 'in-fullscreen-changed' in (r/'extension/extension.js').read_text()
assert 'protect-fullscreen' in (r/'extension/prefs.js').read_text()
assert 'app/hdr10_patterns.py' in [str(x.relative_to(r)) for x in r.glob('app/*.py')]
assert 'sdr-color-studio-hdr-test' in (r/'install.sh').read_text()
assert (r/'assets/hdr10-reference-steps.mp4').is_file()
assert (r/'assets/hdr10-reference-steps.mp4').stat().st_size > 2000
installer=(r/'install.sh').read_text()
assert 'install -m 644 \"$ROOT/extension/prefs.js\"' in installer
patch=(r/'patches/mutter-51-sdr-white-1624.patch').read_text()
assert '-                            "brightness-max", 210,' in patch
assert '+                            "brightness-max", 800,' in patch
# Unit-test the PKGBUILD injection without running makepkg/network.
import importlib.util
spec=importlib.util.spec_from_file_location('inject',r/'scripts/inject-pkgbuild.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory() as directory:
    recipe=pathlib.Path(directory)/'PKGBUILD'
    recipe.write_text('pkgname=mutter\npkgver=51.0\npkgrel=1\nsource=(mutter.tar.gz)\nb2sums=(SKIP)\nprepare() { echo Arch-original; }\n')
    f=pathlib.Path(directory)/'sdr-color-white-ceiling.patch'
    f.write_text(patch)
    mod.inject(recipe, f)
    after=recipe.read_text()
    assert 'pkgrel="${pkgrel}.9001"' in after
    assert 'sdr_color_upstream_prepare' in after
    assert 'patch --batch --forward --fuzz=0 --dry-run' in after
    assert 'b2sums+=' in after
    try: mod.inject(recipe, f)
    except SystemExit: pass
    else: raise AssertionError('Duplicate injection was not rejected')
print('Python, JSON, XML and PKGBUILD injection checks: OK')
PY_CODE
if command -v glib-compile-schemas >/dev/null; then
  glib-compile-schemas --strict --dry-run "$root/extension/schemas"
  echo 'GSettings schema: OK'
fi
if command -v node >/dev/null; then
  node --check "$root/extension/extension.js"
  node --check "$root/extension/prefs.js"
  echo 'GNOME extension JavaScript syntax: OK'
fi
python3 -B "$root/tests/test_hdr10_patterns.py"
echo 'Static and PQ signal generation unit checks passed. Does not prove GNOME 51 runtime / display calibration.'
