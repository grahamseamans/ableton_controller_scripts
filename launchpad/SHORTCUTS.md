# SHORTCUTS — LPX Script

What is unverified, janky, or left for later, plus the in-Live checklist. The pure modules'
self-checks pass (`uv run python layout.py | led.py | palette.py | snapshot_store.py |
drum_maps/__init__.py`), and every file passes `python -m py_compile`. Nothing below has
run in Live yet.

## [SOLID] ran in Live with the Jomox script (archived)

- The note API: `clip.get_notes_extended`, `Live.Clip.MidiNoteSpecification(...)` +
  `add_new_notes`, `apply_note_modifications` (velocity), `clip_slot.create_clip`.
- Listeners: single `@listens("value")` on buttons and matrices, where the matrix event is
  `(value, column, row, is_momentary)`. Also `listens_group("has_clip")`, clip `notes` and
  `playing_position`, and `song.view` `selected_track`.
- `IdentifiableControlSurface.on_identified` → Programmer mode, and `disconnect` → Live mode.
- `Layer(name=element)` calling `set_<name>`.

## [GUESS] new here, check in Live

- **ModesComponent / Layer hand-off order.** Mode steps are clear → enable → LayerMode →
  repaint. Leaving runs them in reverse. From `mode.py`, `StackingResource` runs the old
  page's leave before the new page's enter. Check that nothing stale is left after a switch
  and that no press reaches a hidden page.
- **Clip colour → RGB.** `clip.color` 0xRRGGBB is converted by dropping 1 bit per channel.
  Colours may look washed out or too dark on the LPX. Compare them against Live.
- **Animation timer.** `task.loop(task.wait(0.25), task.run(...))` on the session page
  toggles bright/dim. Check the timer runs, and that it pauses when the page is disabled.
- **The `set_data` dirty flag.** Does `song.set_data` alone mark the set as modified
  (asterisk / save prompt)? If it doesn't, a snapshot can be lost when you close the set.
- **Script re-instantiation on set load.** The snapshot store is read in the constructor and
  on page entry. This assumes Live re-creates the script when a set loads. If it doesn't,
  entering the page re-reads the store anyway.
- **Plugin device-name matching.** Matching is on `device.name`: "Drumazon 2", "Microtonic"
  and "MicrotonicMulti", case-insensitive, top-level devices only. Check the real
  `device.name` / `class_display_name` in Live. A renamed device won't match, and renames
  aren't listened to (only the `devices` list is).
- **Drumazon notes.** The note numbers were read from a manual screenshot, assuming
  C0 = 24. The channel behaviour is undocumented.
- **Microtonic receive channel.** It must be "any" or 1, and pitched mode must be off. The
  factory default isn't documented.
- **New Live calls not used by the Jomox script:**
  - `clip.remove_notes_by_id` (step toggle-off, lane clear);
  - `apply_note_modifications` changing `start_time` (nudge);
  - `clip_slot.set_fire_button_state` / `scene.set_fire_button_state`;
  - `track.stop_all_clips`, `song.stop_all_clips`;
  - `clip_slot.duplicate_clip_to`;
  - `track.playing_slot_index >= 0` as "column is playing";
  - `listens_group("value")` over mixer volume parameters;
  - song `return_tracks` / `scenes` listeners;
  - `listenable_property` (`super_held`) and `__events__` (`bound_track`) on components.
- **Clip loop API.** `Live.Clip.Clip` `loop_start`, `loop_end`, `end_marker`
  (get/set) and the `loop_start` / `loop_end` listeners are all in the Live 12 LOM mirror
  (`knowledge_base/ableton/scripting/midi_remote_api/structure_void_mirror/midiremotescripts.structure-void.com/reference/live12/Live.Clip.runtime/`).
  What's unverified:
  - **Growing past the end marker.** Setting `loop_end` beyond `end_marker` might raise
    or clamp. The code pushes `end_marker` out first.
  - **Created clip loop.** This assumes a clip created by `create_clip` has `looping` on
    and `loop_start = 0`. A clip whose loop doesn't start at 0 logs a warning, because
    the steps assume clip time 0.
  - **Units.** The loop is read in beats. The LOM says beats or seconds depending on
    warping; MIDI clips should be beats.
  - **Playhead position.** The playhead is `int(playing_position / resolution)`, which
    assumes `playing_position` is clip time inside the loop. The old code wrapped
    position modulo the loop instead.
- **Snapshot recall and listeners.** During a recall the volume listener is muted by a flag.
  This assumes Live fires parameter listeners synchronously inside the setter.

## Janky, fix later

- **Session repaints by polling.** The session page repaints every 0.25 s (only changed
  LEDs are sent) instead of listening to each slot, clip, track and scene property. Clip
  colour, arm, recording and triggered states can show up to 0.25 s late. Ring moves and
  super repaint immediately.
- **32-step window only.** Nudge, clear lane and velocity act only on on-grid notes inside
  the 32-step window. Nudge refuses (logged) when the clip's loop is longer than 32 steps. Off-grid notes play but are never shown or edited.
- **Clip creation.** A clip created by the first drawn step is 32 steps at the resolution
  current at that moment.

## In-Live checklist

### Phase 1: skeleton
- [ ] Remove the old `Jomox_Pattern_Programmer` folder from Live's MIDI Remote Scripts, then
      install `LPX_Script`. Both scripts auto-detect the same LPX.
- [ ] Log.txt has no traceback, and the device enters Programmer mode.
- [ ] Session, Note and Custom switch the logo and page-button LEDs.
- [ ] Capture MIDI lights super while held.
- [ ] Disabling the script returns the device to Live mode.

### Phase 2: snapshot page
- [ ] Super + pad saves, and pad recalls.
- [ ] A stored slot is ¼ brightness and the active slot is full brightness.
- [ ] Moving any track or return fader clears the active mark.
- [ ] Snapshots survive saving, closing and reopening the set.
- [ ] Check whether `set_data` alone marks the set dirty.

### Phase 3: drum page (test on a Drumazon 2 track and a Microtonic track)
- [ ] Steps write the map notes. Verify every Drumazon voice by ear and in the piano roll.
- [ ] The playhead is correct.
- [ ] The velocity column works (held step and default).
- [ ] ▲ + step changes the clip's loop in Live, including growing past the end marker and on an empty slot.
- [ ] Editing the loop in Live updates the pads, and each pattern keeps its own length.
- [ ] Resolution and Nudge work.
- [ ] Super + pattern pad duplicates the current pattern.
- [ ] Super + voice pad clears that lane.
- [ ] Editing in the piano roll repaints the pads.
- [ ] A track with no matching plugin shows red voice pads, presses are logged, and nothing
      is written.
- [ ] Session → drums → session keeps the selected voice, pattern, resolution and length.

### Phase 4: session page
- [ ] Pad colours match Live's clip colours, and launching works (including gate launch mode).
- [ ] Playing clips pulse, triggered clips flash, recording pulses red, and empty slots on an
      armed track are dim red.
- [ ] Scene launch works.
- [ ] Ring navigation works, and the arrows dim at the edges of the set.
- [ ] Super + pad stops that track. Super + scene button stops all clips.
- [ ] No stale LEDs after switching pages.
