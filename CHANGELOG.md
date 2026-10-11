# v0.3.1

- Added a minimal SVG brand mark and installed desktop icon.
- Added the user-provided GNOME preferences screenshot and updated the GitHub README.
- Added automatic locale selection and an explicit language selector with partial EN, DE, ES, IT and PT-BR translations (French source strings).
- Existing HDR capabilities are unchanged.

# Changelog

## v0.3.0 — Experimental HDR10 patterns and fullscreen safeguards

- Added a reproducible HDR10 (PQ, BT.2020, HEVC Main 10) test-pattern generator
  and bundled ready-to-play clip, both with independently verifiable stream
  metadata, absolute PQ signal targets and near-black checks.
- Added **Protect fullscreen apps** GSettings option (on by default) to stop
  the global GNOME shader when any monitor has a fullscreen window.
- Added fullscreen/SDR limitations prominently in the README: windowed HDR
  remains unsafe for full color correction, physical nits cannot be inferred.
- Added GTK4 buttons to generate (async, without UI freeze) and play patterns.
- Renamed the HDR white control to clarify reference white vs real screen nits.
- Added Python PQ sample-value tests and end-to-end HEVC stream verification
  in the GitHub Actions workflow.
- Retained the 51.x-only safety checks and optional package build.

## v0.2.1

- Added `prefs.js` for GNOME Extensions preferences and per-monitor GUI.

## v0.2.0

- Added Arch official source PKGBUILD fetching, compatibility checks, CI,
  optional reference-white patch, per-monitor GTK4 color controls.
