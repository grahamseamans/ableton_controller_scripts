# Ableton Extensions SDK — (gated, manual download)

The Extensions SDK docs are behind a **beta login** (`ableton.centercode.com`); the public
page (https://ableton.github.io/extensions-sdk/) is only a stub, so `update.py` can't fetch
them. When you have beta access, download the SDK docs/examples and drop them **here** —
this folder is committed (not gitignored), unlike the auto-fetched sources.

**Context:** Extensions are a JS/TS + Node system for *in-DAW tools* (context-menu actions,
dialogs, webview panels) with Live Object Model access. They do **not** do hardware control
surfaces or real-time MIDI I/O — so they're not usable for the controller projects
(Launchpad/Faderfox/AlphaBase). Archive for reference; possible future use for in-Live setup
automation (e.g. scaffolding the AlphaBase 11-track template). See `../../../README.md`.
