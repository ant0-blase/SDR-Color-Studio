# Contributing

Contributions and bug reports are welcome. Include GNOME Shell version,
Mutter version (`pacman -Q mutter`), GPU model, `gdctl show --verbose`
(redact any serial IDs), and reproduction steps. Test in a secondary user
session when possible: the compositor is critical infrastructure.

Run `make test` before submitting a pull request. GitHub Actions runs
static syntax/patch checks; visual, monitor-specific HDR correctness must
be tested on actual GNOME 51 Wayland hardware.

Please don't claim hardware nits from the nominal `gdctl` reference value.


## Translation contributions

Interface translations live in `extension/i18n.json`. French phrases are the source keys; `en` is the fallback for unknown locales. To add a language, add its locale code (for example `nl`) and translate the existing keys. Use UTF-8 and keep technical terms like `bt2100`, `gdctl`, `PQ` and units unchanged.

The **Language / Langue** dropdown is defined in `extension/prefs.js` (the `LOCALES` array); add your locale there to make it selectable. The GTK application reads the same language from GSettings. Static messages still need wider translation coverage—pull requests are welcome. Run `make test` before submitting.
