# Jomox Pattern Programmer — Architecture

## Vision

A **Novation Launchpad X** turned into a **drum pattern programmer for the Jomox
AlphaBase**, hosted in Ableton Live. You program patterns on the Launchpad; they are
**standard Live MIDI clips** that play the AlphaBase and persist with the Live set. The
Launchpad script is purely the **editor + display** — it never makes sound and never
routes audio/MIDI to the AlphaBase; normal Live clip playback does that.

This is part of the wider "make Ableton immediate" effort alongside `faderfox_controller`.

## The core decision: AlphaBase channel-16 keymap mode

The AlphaBase has two MIDI modes (see `knowledge_base/hardware/jomox_alphabase/notes.md`,
manual §13.1.1):

- **Native mode** — each instrument on its own channel (1–11), note number = full
  chromatic pitch. Rich, but a single Live track outputs only one channel
  (`knowledge_base/.../live_manual`, "Routing and I/O"), so this needs 11 tracks and
  defeats "standard clips on one track."
- **Channel-16 keymap mode** — **one channel**, note number selects the instrument, with
  **4 tunings per instrument** (pitch deltas 0/6/12/18 semitones). ← **we use this.**

Channel-16 mode collapses everything to **one MIDI track → AlphaBase channel 16**. It
solves the multi-channel routing problem entirely and still supports a (4-step) per-step
tuning feature. The cost is only 4 tunings per instrument instead of full chromatic — an
accepted trade for single-track simplicity.

### The keymap (manual §13.1.1) — notes 36–79 on channel 16

| Instrument | Notes | idx | Instrument | Notes | idx |
|---|---|---|---|---|---|
| Kick | 36–39 | 0 | Rim | 56–59 | 5 |
| Snare | 40–43 | 1 | Crash | 60–63 | 6 |
| Closed HH | 44–47 | 2 | Ride | 64–67 | 7 |
| Open HH | 48–51 | 3 | X1 sample | 68–71 | 8 |
| Clap | 52–55 | 4 | X2 sample | 72–75 | 9 |
| | | | FM synth | 76–79 | 10 |

**Note formula:** `note = 36 + instrument_idx*4 + tuning` where `tuning ∈ {0,1,2,3}`
(→ 0/6/12/18 semitones). Default `tuning = 0`.

## Data model

- **A pattern = a Live MIDI clip** in a slot on the single track. Bottom-right pads select
  the slot. Patterns persist with the set. ✔ "stick around after saving."
- **A step = presence/absence of a note** at the step's clip time, for the selected
  instrument, at that step's chosen tuning. Toggling a step adds/removes one note.
- **Step time** = `step_index * step_resolution` (default 1/16). 32 steps fit the top half
  with no paging.
- The script keeps a lightweight in-memory mirror of the clip's notes for fast LED
  redraws, but **the clip is the source of truth** (listen for external edits).

Live 12 note API (modernised from Launchpad95's older `select_all_notes` /
`replace_selected_notes` dance — see `knowledge_base/.../midi_remote_scripts/Live12` and
the structure-void mirror): `clip.get_notes_extended`, `add_new_notes`,
`remove_notes_extended`, `apply_note_modifications`. Playhead from `clip.playing_position`.

## The Launchpad X surface (programmer mode)

Enter programmer mode on connect (`F0 00 20 29 02 0C 0E 01 F7`), revert to Live mode on
disconnect (`…0E 00 F7`). Full button map + LED facts in
`knowledge_base/hardware/novation_launchpad_x/notes.md`. Region layout:

```
 top round row: CC 91..98   ── editing functions ──
┌───────────────────────────┐
│  STEP SEQUENCER  (8×4=32)  │  grid rows 8→5 (notes 81-88,71-78,61-68,51-58)   ▕ right
│  step 1 = top-left (81)    │  step order: left→right, top→down                 ▕ round
├─────────────┬─────────────┤                                                   ▕ col
│ INSTRUMENT  │  PATTERN     │  grid rows 4→1                                    ▕ CC
│ select 4×4  │  select 4×4  │  L: notes 41-44,31-34,21-24,11-14                 ▕ 19,29
│ (11 used)   │  (16 slots)  │  R: notes 45-48,35-38,25-28,15-18                 ▕ ..89
└─────────────┴─────────────┘
```

- **Step sequencer (rows 5–8, 32 pads):** the selected instrument's pattern. Tap = toggle
  note on/off (at current tuning). LED off = empty; on = coloured by tuning; playhead cell
  = bright/pulsing. Optional "ghost" = other instruments' hits shown dim.
- **Instrument select (bottom-left 4×4):** pads 0–10 = the 11 instruments (5 spare). The
  selected instrument is what the step grid edits. With **Preview** on, tapping auditions
  the instrument (routed via the armed track, Launchpad95-style — see below).
- **Pattern select (bottom-right 4×4):** 16 clip slots on the track = 16 patterns.
- **Hold-to-tune (the signature feature):** while a step pad is held, the bottom-left 4×4
  becomes a **tuning picker** (4 options); tapping sets that step's note tuning, and the
  step's colour changes to match. Release returns bottom-left to instrument select.

## LED feedback

Use the Launchpad X **batch RGB SysEx** (command `03`, up to 81 LEDs per message) to
repaint the surface **when the playhead moves to a new step cell** (not on every
`playing_position` update — that fires far more often than steps change) and on edits.
Tuning → fixed colour map (4 colours). A full-surface redraw is cheap; an incremental
diff (Launchpad95-style) is the fallback if needed.

## Required Live setup (one-time template)

1. One **MIDI track**, `MIDI To → <AlphaBase port>, Ch. 16`.
2. AlphaBase set so **RxTrig is on** (receives external note triggers) and it is in the
   channel-16 keymap configuration.
3. Create up to 16 clips in that track's slots = the 16 patterns (or let the script create
   them on demand).

No Drum Rack or instrument is required on the track — the AlphaBase makes the sound; the
track only carries/forwards the MIDI clip on channel 16.

## "Play it in" / preview routing

The script's MIDI output port is the **Launchpad** (for LEDs) — it cannot send to the
AlphaBase directly. So preview/record-in works the Launchpad95 way: the script forwards the
correct keymap note (`36 + i*4 + tuning`) to the **armed track's input**, which sends it out
channel 16 to the AlphaBase (and records it into the clip when armed). This requires the
Launchpad's input port to be **Track-input enabled** in Live's MIDI prefs (or the script's
note-forwarding path); confirm during implementation. The script does not synthesise
playback itself.

## Proposed file structure (not yet built)

```
jomox_pattern_programmer/
  ARCHITECTURE/  architecture.md  midi_mappings.md  history.md
  scripts/Jomox_Pattern_Programmer/
    __init__.py
    lpx_surface.py          # ControlSurface: programmer-mode SysEx, routes grid to components
    lpx_layout.py           # Launchpad X note/CC constants (programmer mode)
    lpx_led.py              # batch-RGB SysEx painter + colour/tuning palette
    sequencer_component.py  # 32-step editor: clip note read/write, playhead, hold-to-tune
    instrument_select.py    # bottom-left: instrument select + tuning picker
    pattern_select.py       # bottom-right: clip-slot (pattern) select
    alphabase_map.py        # instrument×tuning <-> note 36-79 (ch16 keymap), single source
```

Live 12 remote script (`ableton.v2`/`v3` framework). Adapt proven patterns from
Launchpad95 (`/tmp/launchpad95` during research; patterns summarised in chat) but use the
modern Live 12 note API.

## Round buttons (initial — refine in use)

Transport lives on another controller, so all 16 round buttons serve programming:

- **Top row (CC 91–98):** step resolution (1/8·1/16·1/32), accent level, ghost overlay,
  preview toggle, clear (lane; +Shift = pattern), undo (+Shift redo), nudge/rotate, Shift.
- **Right column (CC 19–89):** mute / solo selected instrument, copy / paste / duplicate
  pattern, + spare.

## Open decisions / verify on hardware

- **MIDI velocity** — does the AlphaBase respond to incoming velocity for dynamics/accent
  in ch16 mode? (Its internal sequencer uses 63/127 — manual §10.3.1.) Drives the Accent button.
- **Pattern length** — patterns can be shorter than 32 steps ("32 *max*"). Need a way to
  set loop length per pattern (clip loop, or a length control) and reflect it on the grid
  (Launchpad95 used a loop selector for this).
- Confirm the 4 tuning deltas (0/6/12/18 semitones) feel musically useful per instrument.
- Exact round-button assignments (above is a starting point).
- Whether to keep a Drum Rack on the track purely for naming/visual feedback in Live.

### Resolved

- **Ch16 keymap reception** — confirmed (hardware): the AlphaBase receives the channel-16
  keymap from external MIDI. (The manual's §10.3.3 RxTrig text mentions only ch 1–11 and
  omits 16, but ch16 reception works in practice.)

## Non-goals

- **No transport** (play/stop/tempo) — that's a different controller.
- **No native 11-channel chromatic mode** — explicitly traded away for single-track
  simplicity (see history.md). Revisit only if 4 tunings prove too limiting.
- **No audio / no sound generation** — the AlphaBase is the sound source.
- **No standalone sequencer engine** — Live transport plays the clips; the script only edits.
