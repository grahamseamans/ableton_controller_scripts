# Knowledge Base

Shared reference library for the Ableton/hardware projects in this workspace
(`faderfox_controller`, `drum_programmer`, …). Projects hold **only their own code
and project docs**; all manuals, SDK docs, and reference source code live here.

## Keeping it current

Everything is defined declaratively in [`sources.yaml`](sources.yaml) and refreshed by
[`update.py`](update.py):

```bash
# refresh everything (resumable — safe to cancel and re-run)
uv run --with pyyaml python update.py

# refresh specific sources
uv run --with pyyaml python update.py ableton_live12_manual max_for_live_docs

# list all sources
uv run --with pyyaml python update.py --list
```

The updater only fetches **new or changed** content (wget `-N` for mirrors, git
fast-forward for repos, timestamp-checked re-download for PDFs). Each run prints a
change report (`+added ~modified -removed`) and appends it to `_UPDATE_LOG.md`, so the
history of "what moved" is recorded. The Live 12 manual PDF auto-tracks its latest dated
URL, so re-running picks up new manual revisions automatically.

To add a source: add an entry to `sources.yaml` (pick a `type`) and re-run. That's it.

## Layout

```
ableton/
  live_manual/        official Live 12 manual PDF (auto-tracks latest)
  scripting/
    midi_remote_scripts/  decompiled stock scripts: Live 9/10/10.1/11/12 + laidlaw42
    midi_remote_api/      structure-void mirror (best LOM / framework reference)
    extensions_sdk/       NEW JS/TS system — GATED (see below)
  max_for_live/       Max + Max-for-Live docs mirror (cycling74)
hardware/
  novation_launchpad_x/   programmer reference + user guide PDFs + notes.md
  jomox_alphabase/        manual PDFs + notes.md (MIDI implementation decoded)
  faderfox/               MX12/PC12 manuals, firmware, templates (vendored static)
```

## The Ableton scripting generations (so we don't conflate them)

1. **`_Framework`** — original Python control-surface framework (Live 8/9, Python 2).
2. **`ableton.v2.control_surface`** — component-based framework (Push 2 era, ~Live 9.5/10).
3. **Python 3 migration** (Live 11, 2021) — Py2 scripts stop working.
4. **`ableton.v3`** — further framework evolution (Live 11–12).
5. **Extensions SDK** — separate JS/TS + Node system (Live 12.4.x, beta). **In-DAW tools
   only (menus/dialogs/webviews); no hardware or MIDI I/O.** Not usable for control
   surfaces — Python remote scripts remain the only path for those.

There is **no first-party documentation** for the Python remote-script system; the
decompiled repos + structure-void are the authoritative references.

## Known gaps / blocked

- **Extensions SDK docs are gated** behind a beta login (`ableton.centercode.com`). The
  public page is a stub. Needs a logged-in manual download — drop the files in
  `ableton/scripting/extensions_sdk/` and they'll be kept. (Low priority — see above.)
- **Live 12 decompiled scripts are partial** — newer Python resists clean decompilation,
  so that repo is less complete than Live 9–11.
