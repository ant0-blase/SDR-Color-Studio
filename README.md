<p align="center">
  <img src="assets/logo.svg" alt="SDR Color Studio logo" width="88" height="88">
</p>

<h1 align="center">SDR Color Studio</h1>

<p align="center"><strong>Per-display color controls and experimental HDR/SDR tuning for GNOME.</strong></p>

<p align="center">
  <a href="https://www.gnome.org/"><img alt="GNOME 51" src="https://img.shields.io/badge/GNOME-51-4A86CF?style=flat-square"></a>
  <a href="https://archlinux.org/"><img alt="Arch Linux" src="https://img.shields.io/badge/Arch-Linux-1793D1?style=flat-square"></a>
  <a href="LICENSE"><img alt="GPL-3.0-or-later" src="https://img.shields.io/badge/License-GPL--3.0--or--later-555?style=flat-square"></a>
</p>

<p align="center">
  <a href="#features">Features</a> · <a href="#installation">Installation</a> · <a href="#hdr-and-limitations">HDR and limitations</a> · <a href="#localization">Localization</a> · <a href="docs/README.fr.md">Français</a>
</p>

---

SDR Color Studio combines a **GNOME Shell extension**, its native **GNOME Extensions preferences**, and a **GTK4 / libadwaita** companion app. Fine-tune the appearance of each display without switching desktop environments.

## Screenshot

![SDR Color Studio preferences on GNOME 51, in French](assets/screenshots/preferences-fr.png)

*Actual GNOME 51 preferences UI. The values shown are user-selected examples, not a recommended calibration.*

## Features

| Feature | How it works |
| --- | --- |
| Per-monitor color profiles | Save saturation, contrast, gamma and software brightness for each display connector. |
| SDR reference white in HDR mode | Ask Mutter for a nominal reference-white level via `gdctl` on supported `bt2100` outputs. |
| Native GNOME preferences | Open the controls through the **Extensions** application or the GTK4 app. |
| Fullscreen protection | Optionally suspend the extension's color effect while any application is fullscreen. |
| HDR10 test patterns | Bundled HEVC Main 10 / BT.2020 / PQ test clip and a reproducible generator. |
| Optional Mutter patch | Build against the current *compatible* Arch Mutter source to expand its reference-white adjustment range. |

## Installation

**Requirements:** GNOME Shell **51.x** on Arch Linux, GTK4/libadwaita, `python-gobject`, `gdctl` and `gnome-extensions`. Wayland is recommended.

```bash
sudo pacman -S --needed python-gobject gtk4 libadwaita glib2 ffmpeg mpv

# In the cloned or extracted project directory:
./install.sh
```

Open the preferences directly:

```bash
gnome-extensions prefs sdr-color-studio@local
```

Or launch the standalone app:

```bash
~/.local/bin/sdr-color-studio
```

> **Already using an older version?** GNOME Shell can cache the extension's `hasPrefs` state. If the Extensions app still claims the extension has no preferences after adding `prefs.js`, log out and back in once. A disable/enable cycle does not always refresh this metadata under Wayland.

### Uninstall

```bash
./uninstall.sh
```

## HDR and limitations

**Reference white is not the same as your monitor's peak luminance.** Mutter's PQ reference level starts at **203 nits**. The UI's reported value is a *requested reference white*, not a reading from your display, and changing it may have no visible effect on some hardware or compositor paths.

- HDR output (`bt2100`) and a compatible `gdctl` backlight preference are required for this control.
- Color sliders use an experimental compositor-level effect; they are **not color calibration** and may alter HDR content.
- Fullscreen protection disables the shader for **all** monitors while an application is fullscreen; HDR video in a window is **not** independently protected.
- The HDR10 test clip sends known *encoded* PQ levels; it does not measure physical luminance or replace a colorimeter.

For details, read [HDR reference and safety](docs/HDR-REFERENCE.md).

### Optional Mutter build

**Not required** for the GUI, color sliders or test patterns. The supplied patch raises Mutter 51's `MetaBacklightRefWhite` upper bound from `210` to `800` (up to ~1,624 nits **requested**). This is an experimental upper-range change, **not** a complete KDE-style per-surface SDR brightness implementation.

```bash
sudo pacman -S --needed base-devel git python patch
./build-mutter.sh

# Review the package and only then opt in to installation:
./install-patched-mutter.sh
```

The script retrieves the current official Arch package recipe and verified sources, checks for compatibility with Mutter **51.x**, and aborts if its patch no longer applies. It **does not** install a system compositor package on its own.

Recovery from a normal terminal or TTY (`Ctrl+Alt+F3`):

```bash
./restore-official.sh
# Or manually: sudo pacman -S mutter
```

## HDR10 test clip

The included file is [`assets/hdr10-reference-steps.mp4`](assets/hdr10-reference-steps.mp4). It uses 10-bit HEVC with BT.2020 primaries and the SMPTE ST 2084 (PQ) transfer function, including a 203-nit reference square, brighter steps and near-black patches.

Generate a fresh clip:

```bash
~/.local/bin/sdr-color-studio-hdr-test --output "$HOME/Videos/hdr10-steps.mp4"
```

Use a video player and output path capable of **actual HDR signaling**. SDR tone mapping invalidates visual comparisons.

## Localization

The preferences offer a **Language / Langue** setting. Automatic detection follows your system locale; you can also choose **English, Français, Deutsch, Español, Italiano or Português (Brasil)** manually. Reopen the preferences after changing languages. Unknown locales fall back to English.

Localization is **in progress**: the primary controls are translated for these languages, but some explanatory and diagnostic messages still appear in French or English. We do **not** claim that every language is fully translated.

Translations live in [`extension/i18n.json`](extension/i18n.json). See [CONTRIBUTING.md](CONTRIBUTING.md) to add a language or improve a translation.

## Development

```bash
make test
```

The CI pipeline performs syntax and static checks as well as HDR10/PQ test-clip validation. **Passing those tests does not verify GNOME Shell rendering, HDR accuracy or successful installation on a physical monitor.** Hardware and fullscreen behavior must be tested on a GNOME 51 Wayland session.

Repository layout:

```text
extension/       GNOME Shell effect, preferences, GSettings schema
app/             GTK4 control panel and HDR10 pattern generator
extension/i18n.json   Language packs for preferences and the GTK4 app
assets/          Logo, screenshots and bundled HDR10 test clip
patches/         Optional Mutter reference-white range patch
scripts/         Arch PKGBUILD patch injection
.github/         CI workflow
```

## Contributing and security

Bug reports should include your GNOME Shell version, display connector, output color mode, `gdctl show --verbose` (remove identifying data), and the exact steps to reproduce. Before reporting a rendering issue, check whether it happens with the extension disabled.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [release notes](CHANGELOG.md).

## License

**GPL-3.0-or-later**. The optional Mutter patch builds upon upstream GNOME Mutter, which has its own licensing terms. See [LICENSE](LICENSE).
