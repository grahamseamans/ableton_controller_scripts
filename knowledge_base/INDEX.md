# Knowledge Base — Index

Catalog of what's in the shared reference library and where it came from. For *how* the
refresh system works, see [`README.md`](README.md). To populate/refresh the fetched
content (it's gitignored — reproducible, not committed):

```bash
uv run --with pyyaml python update.py
```

## Catalog

| Source | Type | Location | Size / count | Provenance |
|--------|------|----------|--------------|------------|
| Live 12 manual | PDF | `ableton/live_manual/` | ~97 MB | ableton.com (official, auto-tracks latest dated PDF) |
| Decompiled scripts — Live 9 | git | `ableton/scripting/midi_remote_scripts/Live9/` | ~954 py | github.com/gluon |
| Decompiled scripts — Live 10.1 | git | `…/Live10.1/` | ~989 py | github.com/gluon (covers Live 10) |
| Decompiled scripts — Live 11 | git | `…/Live11/` | ~1150 py | github.com/gluon |
| Decompiled scripts — Live 12 | git | `…/Live12/` | ~1271 py | github.com/gluon (⚠ partial — see gaps) |
| Py3 script mirror | git | `…/laidlaw42_py3/` | small | github.com/laidlaw42 |
| LOM / framework reference | wget | `ableton/scripting/midi_remote_api/structure_void_mirror/` | ~1472 pages / 218 MB | midiremotescripts.structure-void.com (unofficial — best there is) |
| Extensions SDK | gated | `ableton/scripting/extensions_sdk/` | — | **blocked** (beta login) — see gaps |
| Max / Max-for-Live docs | wget | `ableton/max_for_live/mirror/` | ~261 pages / 34 MB | docs.cycling74.com — see [notes](ableton/max_for_live/notes.md) |
| Launchpad X | PDF | `hardware/novation_launchpad_x/` | prog ref + user guide | Focusrite/Novation — see [notes](hardware/novation_launchpad_x/notes.md) |
| Jomox AlphaBase | PDF | `hardware/jomox_alphabase/` | manual + Mk2 | jomox.de — see [notes](hardware/jomox_alphabase/notes.md) (MIDI decoded) |
| Faderfox MX12/PC12 | static | `hardware/faderfox/` | manuals, firmware, templates | vendored (V04, committed) |
| D16 Drumazon / Drumazon 2 | PDF | `plugins/d16_drumazon/` | v1 + v2 manuals | d16.pl — see [notes](plugins/d16_drumazon/notes.md) (MIDI drum map) |
| Sonic Charge Microtonic | PDF | `plugins/sonic_charge_microtonic/` | user guide v3.3.4 | soniccharge.com — see [notes](plugins/sonic_charge_microtonic/notes.md) (MIDI key map) |

## Our synthesis notes (committed, the high-value distillations)

- [`hardware/jomox_alphabase/notes.md`](hardware/jomox_alphabase/notes.md) — AlphaBase MIDI
  implementation decoded: native mode = 11 channels (one per instrument), **note number =
  pitch**; the design wrinkle this creates for `drum_programmer`.
- [`hardware/novation_launchpad_x/notes.md`](hardware/novation_launchpad_x/notes.md) —
  verified programmer-mode contract (grid `11–88`, top CC `91–98`, right CC `19–89`,
  batch-RGB SysEx feedback).
- [`plugins/d16_drumazon/notes.md`](plugins/d16_drumazon/notes.md) — Drumazon GM drum map
  (35–51 → BD…RD), remappable; MIDI channel undocumented.
- [`plugins/sonic_charge_microtonic/notes.md`](plugins/sonic_charge_microtonic/notes.md) —
  36–43 trigger ch 1–8; remappable keys; receive channel/any, pitched mode = ch 1–8 + 10.
- [`ableton/max_for_live/notes.md`](ableton/max_for_live/notes.md) — what M4L is good for
  vs remote scripts vs Extensions.
- Scripting generations overview lives in [`README.md`](README.md).

## Known gaps

- **Extensions SDK docs are gated** behind a beta login (`ableton.centercode.com`); the
  public page is a stub. Needs a logged-in manual download into
  `ableton/scripting/extensions_sdk/` (that path is committed, not ignored). Low priority —
  Extensions can't do hardware/MIDI, so not usable for the controller projects.
- **Live 12 decompiled scripts are partial** — newer Python resists clean decompilation, so
  the Live 12 repo is less complete than Live 9–11. Cross-reference Live 11 when a class is
  missing.
