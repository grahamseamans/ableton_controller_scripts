# MIDI Mappings — Source of Truth

This file is the contract between the Launchpad X, the script and the drum plugins. Sources:
- LPX Programmer's Reference (`/workspace/controller-system/reference/novation-launchpad-x-programmers-reference.pdf`)
- `knowledge_base/hardware/novation_launchpad_x/notes.md`

## Launchpad X, Programmer mode, channel 1

| Control | Message | Numbers |
|---|---|---|
| 8×8 grid | Note | `row*10+col`, bottom-left `11`, top-right `88` |
| ▲ ▼ ◀ ▶ | CC | `91 92 93 94` |
| Session / Note / Custom / Capture MIDI | CC | `95 96 97 98` |
| Right column | CC | `19 29 … 89` (bottom→top) |
| Logo (LED only) | CC | `99` |

- Enter Programmer mode: `F0 00 20 29 02 0C 0E 01 F7`. Back to Live mode: `…0E 00 F7`.
- LEDs: batch RGB `F0 00 20 29 02 0C 03 (03 idx r g b)… F7`, at most 81 per message.

## Buttons

| Button | Session page | Drum page | Snapshot page |
|---|---|---|---|
| Session CC95 | → session | → session | → session |
| Note CC96 | → drums | → drums | → drums |
| Custom CC97 | → snapshots | → snapshots | → snapshots |
| Capture MIDI CC98 | super (hold) | super (hold) | super (hold) |
| ▲ CC91 | ring up | Length (hold) | dark |
| ▼ CC92 | ring down | Resolution (hold) | dark |
| ◀ ▶ CC93/94 | ring left/right | nudge lane | dark |
| Right column | scene launch, top = scene 1 | velocity, 8 levels, bottom = quiet | dark |
| Logo | page signature colour | ← | ← |

## Grid regions

**Session page:** all 64 pads = clip slots of the ring (column = track, row = scene).
- super + pad stops that track.
- super + scene button stops all clips.

**Drum page** (`row 8` = top):

| Region | Pads | Function |
|---|---|---|
| Steps (rows 8→5) | 81–88, 71–78, 61–68, 51–58 | 32 steps, step 1 = `81`, left→right then down. time = step × resolution |
| Voices (rows 4→1, cols 1–4) | 41–44, 31–34, 21–24, 11–14 | DrumMap voices in pad order. super + pad clears that lane |
| Patterns (rows 4→1, cols 5–8) | 45–48, 35–38, 25–28, 15–18 | clip slots 0–15. super + pad duplicates the current pattern there |

- Hold ▲ and tap a step: sets the bound clip's loop to end after that step
  (`loop_end = loop_start + steps × resolution`, and `end_marker` is pushed out if needed).
  The loop shown on the steps always comes from the clip's own `loop_start`/`loop_end`, so
  every pattern keeps its own length, and a loop edited in Live shows up on the pads.
  With no clip in the slot, ▲ + step first creates the clip.
- Hold ▼ and tap one of the first 6 steps: 1/4 · 1/8 · 1/16 · 1/32 · 1/8T · 1/16T (default 1/16).
- Hold a step and press the right column: sets that step's velocity. With no step held, it
  sets the velocity for new steps.

**Snapshot page:** 64 pads = 64 slots, keyed by grid note.
- pad = recall;
- super + pad = save.

## Drum notes

`scripts/LPX_Script/drum_maps/*.py` is the **only** place note numbers live:
- `drumazon2.py`: GM-style, BD 36 … RD 51. UNVERIFIED (read from a screenshot).
- `microtonic.py`: Ch1…Ch8 = 36…43.

Plugin channel notes:
- **Microtonic**: set Receive Channel to "any" or 1, and don't use pitched MIDI mode.
- **Drumazon 2**: channel behaviour is not documented; verify in Live.

Both assume the plugin's factory map.

## Channels

- Launchpad ↔ script: channel 1, on the LPX MIDI port.
- Track → plugin: whatever the track sends. The clips carry only the notes above.
