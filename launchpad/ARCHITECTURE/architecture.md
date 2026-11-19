# LPX Script — Architecture

## Vision

One Novation Launchpad X turned into a composition controller in Live (`docs/overview.md`),
with three pages:

| Page | Button | Doc |
|---|---|---|
| Session: clips, scenes, ring | Session (CC95) | `docs/session.md` |
| Drums: 32-step lane editor for a drum plugin | Note (CC96) | `docs/drums.md` |
| Snapshots: 64 mixer-volume snapshots | Custom (CC97) | `docs/mixer_snapshot.md` |

Capture MIDI (CC98) is **super**, a momentary hold that gives each page a second action.
The script edits Live objects (clips, mixer) and draws LEDs, and it never makes sound.
Code: `scripts/LPX_Script/`. The old Jomox AlphaBase programmer is archived in
`archive/jomox_pattern_programmer/`.

## Device

Programmer mode (LPX Programmer's Reference; `knowledge_base/hardware/novation_launchpad_x/`).
`IdentifiableControlSurface.on_identified` enters Programmer mode and `disconnect` returns
the device to Live mode (proven in the archived script).

## Pages = modes

`surface.py` owns one v2 `ModesComponent("Pages")`. Each mode enters, in order:

1. clear the page LEDs (grid, right column and arrows: 76 LEDs in one batch),
2. enable the page's components,
3. a `LayerMode(component, Layer(...))` per component,
4. `repaint_page` (last, because a Layer grab resets its elements to 0).

- Page components get pads, arrows and the right column **only through Layers**. A disabled
  page holds no elements, so it can't see another page's presses. Disabled components keep
  their state.
- `GlobalControlsComponent` owns the page buttons, super and the logo. It is always on and
  never in a page Layer, so it binds its buttons directly. Pages subscribe to its `super_held`
  event.
- The script always opens on the session page.

## One LED system, one colour principle

- All LEDs are batch-RGB SysEx through `led.LedPainter`.
- No framework Skin and no palette indices. That is why the session page uses only
  `SessionRingComponent` from the framework: `SessionComponent` and
  `SessionNavigationComponent` light their buttons through the Skin. Launching, stopping and
  moving the ring are done in `session_page.py` itself.
- All colours are in `palette.py`, grouped by page.
- Each page has a signature colour (page button, logo), and **no colour repeats within a
  page**, so any pad that changes meaning under a hold also changes colour. The self-check
  enforces this.
- The session page shows Live's clip colours. Pulse and flash are one timer in
  `session_page.py`.

## Session page

8×8 ring (own `SessionRingComponent` per instance). Pads fire and release clip slots with
`set_fire_button_state` (this respects launch modes). The right column launches scenes and
the arrows move the ring one step.

Super actions:
- super + pad stops that track;
- super + scene button stops all clips.

## Drum page

- `drum_page.py` coordinates `SequencerComponent` (rows 8–5), `VoiceSelectComponent`
  (bottom-left 4×4) and `PatternSelectComponent` (bottom-right 4×4 = first 16 clip slots).
- The target track comes only through `track_binding.current_track()`, which follows
  `song.view.selected_track`. The script only reads it.
- **Drum maps** (`drum_maps/`) are the single source of note numbers. A `Voice` writes
  `note` and reads its lane as `{note} ∪ also_matches`. The map is picked by matching a
  device name on the track (case-insensitive). With no match, the drum controls do nothing,
  the voice pads show the error colour, and the press is logged.
- A pattern is a Live MIDI clip. The clip is the source of truth and its notes are cached per
  lane for drawing.
- A pattern's length is its clip's loop. There is no loop window on the script side: ▲ + step
  writes the clip's `loop_end`, and the steps read `loop_start`/`loop_end` back through listeners.

## Snapshot page

- `snapshot_store.py` holds the pure logic: the format, capture, apply, name matching, and
  read-modify-write of `song.set_data("lpx_script.mixer_snapshots", json)`.
- `snapshot_page.py` handles the grid, the in-memory active mark, and volume listeners over
  every track and return. A volume move of more than 1e-4 clears the active mark.

## Two Launchpads (not built, not blocked)

- No module-level mutable state.
- The script never changes the selected track.
- The drum target goes through the binding seam.
- Each instance has its own ring.
- Snapshot writes are read-modify-write on the shared key.
- Nothing depends on a unique port name.

## Files

- **pure**: no Live import, `uv run python <file>` self-checks.
- **live**: imports the framework and only runs in Ableton.

| File | Kind | Role |
|---|---|---|
| `__init__.py` | live | capabilities, create_instance |
| `surface.py` | live | device mode, page modes |
| `elements.py` | live | every element |
| `global_controls.py` | live | page buttons, super, logo |
| `session_page.py` | live | session page |
| `drum_page.py`, `sequencer_component.py`, `voice_select.py`, `pattern_select.py` | live | drum page |
| `snapshot_page.py` | live | snapshot page |
| `layout.py`, `led.py`, `palette.py`, `snapshot_store.py`, `drum_maps/` | pure | numbers, LEDs, colours, store, maps |

## Code pattern

- Listeners are single-underscore `@listens` handlers bound with `self._on_x.subject = ...`.
- Components get elements through `set_<name>` Layer setters.
- A disabled component never paints.
- Nothing fails quietly: bad data raises, and ignored presses are logged to Live's `Log.txt`.
