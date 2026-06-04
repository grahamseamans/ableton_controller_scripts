# SHORTCUTS / In-Live verification checklist — Jomox Pattern Programmer

Everything here is either (a) a framework/Live API I matched to the decompiled Live 12
scripts and the structure-void LOM but could NOT execute outside Ableton, or (b) a real
in-hardware behaviour the architecture itself flagged "verify on hardware". The three
pure-logic modules (`alphabase_map.py`, `lpx_layout.py`, the SysEx builder + palette in
`lpx_led.py`) ARE verified — their `__main__` self-checks pass under `uv run python <file>`.

Status legend: [SOLID] confident, matches a decompiled reference exactly · [GUESS] best
effort, needs an in-Live test · [HW] hardware/Live-routing question from the architecture.

## A. Framework wiring I could not run (need an in-Live smoke test)

1. [GUESS] `@listens(...)` subject binding via the name-mangled attribute, e.g.
   `self._JomoxPatternProgrammer__on_velocity_value.subject = self._right_column_matrix`.
   I copied this exactly from the decompiled `launchpad_x.py` / `session_overview.py`
   (`self._SessionOverviewComponent__on_matrix_value.subject = self._buttons`). In real
   (non-decompiled) source this is written `self.__on_velocity_value.subject = ...`; the
   mangled form should be equivalent, but CONFIRM the listeners actually fire in Live. If a
   matrix listener never fires, switch to the plain `self.__on_x.subject = ...` spelling.

2. [GUESS] `ButtonMatrixElement` `value` event signature `(value, column, row, is_momentary)`.
   Taken from `button_matrix.py::on_nested_control_element_value -> notify_value(value, x, y,
   is_momentary)` where x=column, y=row. My step/instrument/pattern index math assumes row 0
   is the TOP row of each submatrix and column 0 is the LEFT. VERIFY a known pad lights/edits
   the expected step (tap top-left step pad -> step index 0 -> clip time 0).

3. [GUESS] Component element wiring through `Layer(step_matrix=...)` calling
   `set_step_matrix`. Matches the `set_button_matrix` idiom in `session_overview.py`. Confirm
   the `set_<name>` setters are invoked when the component is enabled (they should be, since
   I `set_enabled(True)` after assigning `.layer`).

4. [GUESS] Enter-Programmer-mode SysEx timing. ADDRESSED: the surface is now an
   `IdentifiableControlSurface` (like the decompiled `Launchpad_X`/`NovationBase`) and sends
   the enter-Programmer SysEx from an `on_identified()` override AFTER the Universal-Device-
   Inquiry handshake — NOT from `__init__` (which fired before the port/device was confirmed).
   The mode switch goes through a `SysexElement` (`_firmware_mode_switch.send_value(byte)`),
   matching the reference's `firmware_mode_switch` idiom, instead of a raw `_send_midi` tuple.
   STILL NEEDS an in-Live smoke test: confirm (a) the framework actually issues the identity
   request and matches `LPX_PRODUCT_ID_BYTES` so `on_identified` fires, and (b) the LEDs paint
   once it does. The batch-RGB LED paints still go out via the painter's `_send_midi` callback
   (raw tuples), which is unchanged — confirm those reach the device.

5. [GUESS] Reverting to Live mode in `disconnect()` BEFORE `super().disconnect()`, now via
   `_firmware_mode_switch.send_value(LIVE)`. The device must not be left in Programmer mode.
   Confirm the revert SysEx is sent (and that the port is still open at that point).

6. [GUESS] `get_capabilities()` ports. I used `inport/outport(props=[NOTES_CC])` for the
   "LPX MIDI" interface (the stock script uses the DAW interface with SCRIPT/REMOTE for its
   gated protocol, which we deliberately do NOT use). Confirm Live binds the correct LPX MIDI
   port and that the device is auto-detected; if not, the user selects the script + LPX MIDI
   In/Out manually in Live's MIDI prefs.

6b. [GUESS] Hold-step right-column modal feedback. On a step press the sequencer fires a
    `held_step_changed_callback` so the surface repaints the right column to its bright
    "velocity-selector active" state (highlighting the held step's current velocity level),
    and restores the dim idle ramp on release — mirroring the tuning picker. VERIFY in-Live
    that the column visibly recolours on hold and reverts on release.

## B. Clip-note Live API calls (signatures from the structure-void LOM, not executed)

7. [SOLID-ish] `clip.get_notes_extended(from_pitch, pitch_span, from_time, time_span)` ->
   MidiNoteVector of note objects with `.note_id .pitch .start_time .duration .velocity
   .mute`. Signature confirmed in the LOM. Used in `sequencer_component.py`.

8. [SOLID-ish] `Live.Clip.MidiNoteSpecification(pitch=, start_time=, duration=, velocity=,
   mute=)`. LOM `__init__`: `(pitch, start_time, duration [, velocity=100.0 [, mute=False
   [...]]])`. I pass the first five by keyword. Confirm keyword names are accepted (they are
   in the LOM signature) — if not, switch to positional.

9. [SOLID-ish] `clip.add_new_notes(iterable_of_specs)`, `clip.remove_notes_extended(from_pitch,
   pitch_span, from_time, time_span)`, `clip.apply_note_modifications(midi_note_vector)`.
   Signatures from the LOM. The modify path (`_rewrite_note_pitch/_velocity`) mutates the
   objects returned by `get_notes_extended` and passes the SAME vector back to
   `apply_note_modifications`, matched by `note_id` — VERIFY this in-Live (esp. that mutating
   `.pitch`/`.velocity` on the returned note objects and re-applying works as the docs say).

10. [GUESS] Step<->time rounding. `_step_index_for_time` rounds a note's `start_time` to the
    nearest step within `NOTE_TIME_MATCH_TOLERANCE_IN_BEATS` (1e-4). Notes drawn by this
    script land exactly on grid times, but externally-recorded/unquantized notes may not map
    to a step and are dropped from the lane cache (intended — they still play). Confirm the
    tolerance is tight enough not to collide adjacent steps at fine resolutions (1/32, 1/16T).

11. [GUESS] `clip_slot.create_clip(length_in_beats)` on the FIRST step draw into an empty
    slot (`_ensure_clip_for_selected_pattern`). LOM says it throws on non-empty/non-MIDI
    slots; I guard with `has_clip`. Confirm the created clip length (32 steps at default res)
    and that drawing then works.

12. [GUESS] `source_slot.duplicate_clip_to(dest_slot)` for Copy/Paste. Present in the LOM
    ClipSlot methods. My Copy just remembers the source slot index; Paste duplicates into the
    selected slot. VERIFY `duplicate_clip_to` takes a destination clip_slot object.

13. [GUESS] `clip.playing_position` for the playhead. I map `playing_position %
    loop_window` to a step cell and only repaint when the cell changes. Confirm
    `playing_position` is in beats relative to the clip and updates via the
    `@listens("playing_position")` listener (it should — Launchpad95 uses the same listener).

## C. Listeners on Live objects (registration idiom unverified at runtime)

14. [GUESS] `@listens("notes")` on a clip to catch external edits, and `@listens("has_clip")`
    GROUP listener (`@listens_group` + `replace_subjects`) across the 16 pattern clip_slots.
    Confirm these fire; if `notes` isn't a valid listenable on Clip in this Live version, fall
    back to re-reading on selection/playhead changes.

15. [GUESS] `@listens("selected_track")` on `self.song.view` to rebind the AlphaBase track
    when the user selects a different track. Matches `target_track.py`. Confirm.

## D. Hardware / Live-routing questions (the architecture's own "verify on hardware")

16. [HW] PREVIEW / play-in note forwarding. `_forward_preview_note` sends Note On/Off on the
    keymap channel (16) straight out the script's MIDI OUTPUT — but that output port is the
    LAUNCHPAD, not the AlphaBase. As written this will light/► nothing on the AlphaBase. The
    architecture says preview must go via the ARMED TRACK'S INPUT (Track-input-enabled LPX
    port), Launchpad95-style, so Live re-emits it on the track's "MIDI To Ch.16". THIS IS THE
    BIGGEST UNVERIFIED PIECE: confirm whether (a) the LPX input port must be Track-input
    enabled in Live MIDI prefs and the script should NOT send the note at all (Live forwards
    the raw pad press), or (b) the script forwards via a different mechanism. Current code is a
    placeholder that emits to the wrong port; needs the real routing decided in-Live.

17. [HW] AlphaBase velocity response in ch16 keymap mode (architecture "Open decisions").
    The right column offers 8 velocity levels (`VELOCITY_LEVELS_LOW_TO_HIGH`). If the
    AlphaBase only honours normal/accent (63/127, manual §10.3.1), collapse the 8 levels to 2.
    Decide after testing.

18. [HW] The 4 tuning deltas (0/6/12/18 semitones) feeling musically useful per instrument —
    cosmetic, but confirm the tuning picker does something audible.

19. [HW] `RxTrig = on` and ch16 keymap configuration on the AlphaBase (one-time setup). The
    script assumes this; it cannot set it.

## E. Deliberate no-ops / known gaps (documented, not bugs)

20. [SOLID] SOLO (top-row Solo button) is an explicit no-op (`_solo_selected_instrument`).
    The AlphaBase makes the sound, not a Live device, so there is no per-keymap-instrument
    Live object to solo. Left as a no-op rather than faking it. If a real solo is wanted it
    needs AlphaBase-side control (CC mute of the other 10 instruments) — out of current scope.

21. [SOLID] COPY/PASTE operate at clip-slot granularity (whole pattern), not per-lane.
    Matches "copy the current clip / paste into the current slot".

22. [GUESS] NUDGE rotates only the SELECTED instrument's lane within the current loop length,
    by removing+re-adding its notes. Confirm rotation wraps correctly and doesn't disturb
    other instruments' notes (it targets only the selected instrument's 4-note pitch span).

23. [GUESS] Default track selection = "the selected MIDI track is the AlphaBase track."
    There is no explicit AlphaBase-track picker; the script follows the selected track. If the
    user selects a non-MIDI/audio track, all editing controls no-op (intended).
