# HDR10 pattern reference / how to interpret

## What the clip does

The included `assets/hdr10-reference-steps.mp4` is a native ST 2084 (PQ) HDR10
signal in HEVC Main 10, BT.2020 non-constant luminance, TV/limited range.
The generator writes 10-bit Y'CbCr 4:2:0 samples with neutral Cb/Cr=512;
for grayscale samples the coded Y is `round(64 + 876*PQ(luminance_nits))`.
HEVC video metadata includes BT.2020 primaries, SMPTE2084 transfer and
BT.2020-ncl matrix, mastering 0.0001–2000 nits, MaxCLL 2000 and MaxFALL 203.

| Time in clip | Center-square signal |
|---|---:|
| 0–1.5 s | 100 nits |
| 1.5–3 s | 203 nits |
| 3–4.5 s | 400 nits |
| 4.5–6 s | 600 nits |
| 6–7.5 s | 1000 nits |
| 7.5–9 s | 1600 nits |
| 9–10.5 s | 2000 nits |

A small reference patch in the upper-left is always 203 nits. The bottom
shows small patches at 0.005 / 0.01 / 0.05 / 0.1 / 0.5 / 1.0 nit. Their
visibility depends on ambient light, OLED black, video compression and
mapping, not just display capabilities.

## Safe visual check

1. Ensure `gdctl show --verbose` reports `color-mode ⇒ bt2100` for the display.
2. Turn on **Protect fullscreen apps** in the GUI. If the HDR player opens
   in a window, the extension cannot guarantee isolation, so turn off the
   extension's **color corrections** while checking, or play fullscreen.
3. Start the sample in a HDR-capable player; verify it is not SDR-tone-mapped.
4. Look for differences between the 600, 1000 and 1600-nit test *signals*.
   If they look identical it does **not prove** clipping; player tone mapping
   or OS mapping may intentionally compress those signals.
5. Compare window vs fullscreen only as a diagnostic. A signal of 1000 nits
   does not imply your panel actually produced 1000 cd/m².

## What it is not

This package does not install ICC profiles, read a luminance/colorimeter,
automatically discover physical peak brightness, adjust video metadata, or
write EDID. Windows HDR Calibration requires platform integration not
provided by this test generator. Do not treat a bright test pattern as a
calibration measurement.
