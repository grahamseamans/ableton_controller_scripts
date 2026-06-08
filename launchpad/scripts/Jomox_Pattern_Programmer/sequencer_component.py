# -*- coding: utf-8 -*-
"""32-step pattern editor bound to the selected Live clip.

This is the heart of the script. It:
  - binds to the clip in the currently selected pattern slot on the AlphaBase track,
  - draws the 32-step area (rows 8..5) coloured by each filled step's tuning,
  - toggles a step on tap: add/remove ONE note at note = alphabase note for the selected
    (instrument, tuning) and time = step_index * step_resolution_in_beats,
  - while a step pad is HELD, exposes the 4 leftmost bottom-row pads as a tuning picker and
    the right column as a velocity selector, applied to that held step,
  - tracks the playhead from clip.playing_position and only repaints when the playhead moves
    to a DIFFERENT step cell (positions update far more often than steps change).

This module DOES import Live/ableton and therefore can only run inside Ableton. It follows
the decompiled Live 12 `ableton.v2.control_surface` idioms (Component subclass, Layer-wired
`set_<name>` element setters, `@listens` subjects, register_slot for Live-API listeners).

No quiet fallbacks: if there is no clip, every editing control explicitly no-ops (documented
intent), it never fabricates notes or a clip.
"""

from __future__ import absolute_import, print_function, unicode_literals

import Live
from ableton.v2.base import listens, liveobj_valid
from ableton.v2.control_surface import Component

from . import alphabase_map
from . import lpx_layout
from . import lpx_led

# How long a newly drawn note lasts, as a fraction of one step. Kept just under a full step
# so adjacent same-pitch steps remain separate notes (no accidental note merging).
NEW_NOTE_DURATION_AS_FRACTION_OF_STEP = 0.5

# Default velocity (0..127) for a freshly drawn step when no velocity is held/selected.
DEFAULT_STEP_VELOCITY = 100

# The 8 velocity levels selectable on the right column, quietest first. These map the AlphaBase
# velocity-response question (see SHORTCUTS.md) to 8 evenly-spaced MIDI velocities for now.
VELOCITY_LEVELS_LOW_TO_HIGH = (16, 32, 48, 64, 80, 100, 114, 127)

# Floating-point slop when matching an existing note's start_time to a step's time, in beats.
NOTE_TIME_MATCH_TOLERANCE_IN_BEATS = 1.0e-4


class SequencerComponent(Component):
    """Edits the selected clip as a 32-step lane for one (instrument, tuning) at a time."""

    def __init__(self, led_painter=None, *a, **k):
        super(SequencerComponent, self).__init__(*a, **k)
        self._led_painter = led_painter

        # The clip currently being edited (a Live.Clip.Clip or None).
        self._clip = None

        # Editing context, owned here because the step grid needs them on every tap.
        self._selected_instrument_index = 0
        self._default_velocity = DEFAULT_STEP_VELOCITY
        self._step_resolution_in_beats = 0.25  # 1/16 note == 0.25 beats; the documented default
        self._loop_length_in_steps = lpx_layout.STEP_COUNT  # 32 until set via hold-Length

        # Per-step chosen tuning (0..3). Defaults to tuning 0 for every step. This is the
        # script-side intent for drawing NEW notes; existing notes carry their own pitch.
        self._tuning_per_step = [0] * lpx_layout.STEP_COUNT

        # The grid element (rows 8..5), wired in by the surface's Layer via set_step_matrix.
        self._step_matrix = None

        # The currently held step index, or None. Drives hold-step tuning/velocity gestures.
        self._held_step_index = None

        # Optional interceptor set by the surface: step_press_interceptor(step_index) -> bool.
        # When it returns True, a step press is consumed by a top-row hold gesture
        # (Length / Resolution) instead of toggling a note. Default None = always toggle.
        self._step_press_interceptor = None

        # Optional provider set by the surface: ensure_clip() -> a bound clip or None. Called
        # when a step is drawn into a slot that has no clip yet, so the surface can create one
        # on demand (the surface owns clip creation; this component never fabricates a clip).
        self._ensure_clip_provider = None

        # Optional callback set by the surface: held_step_changed() -> None. Fired whenever the
        # held-step state starts or ends, so the surface can recolour the right column to its
        # "velocity-selector active" / idle paint (modal-feedback principle).
        self._held_step_changed_callback = None

        # Last step cell the playhead occupied, so we only repaint on cell changes.
        self._last_playhead_step_index = None

        # Cached snapshot of the clip's notes as {step_index: note_dict} for the selected
        # instrument, for fast LED redraws. The clip remains the source of truth; this is
        # rebuilt whenever the clip's notes change (external edits included).
        self._step_index_to_cached_note = {}

    # ---- element wiring (called by Layer through matching attribute names) --------------

    def set_step_matrix(self, step_matrix):
        if step_matrix:
            step_matrix.reset()
        self._step_matrix = step_matrix
        self._SequencerComponent__on_step_matrix_value.subject = self._step_matrix
        self._repaint_steps()

    # ---- context setters, called by the surface / sibling components --------------------

    def set_selected_instrument_index(self, instrument_index):
        self._selected_instrument_index = instrument_index
        self._rebuild_note_cache()
        self._repaint_steps()

    def set_step_press_interceptor(self, step_press_interceptor):
        self._step_press_interceptor = step_press_interceptor

    def set_ensure_clip_provider(self, ensure_clip_provider):
        self._ensure_clip_provider = ensure_clip_provider

    def set_held_step_changed_callback(self, held_step_changed_callback):
        self._held_step_changed_callback = held_step_changed_callback

    def set_step_resolution_in_beats(self, step_resolution_in_beats):
        self._step_resolution_in_beats = step_resolution_in_beats
        self._rebuild_note_cache()
        self._last_playhead_step_index = None
        self._repaint_steps()

    @property
    def held_step_index(self):
        """The step index currently held down, or None. The surface reads this to know
        whether the right column / option pads should act as velocity / tuning pickers."""
        return self._held_step_index

    def velocity_of_held_step(self):
        """The velocity (0..127) the right-column selector should highlight for the held step:
        the held step's existing note velocity, or the default if it has no note yet. Returns
        None when no step is held (the surface then paints the idle column)."""
        if self._held_step_index is None:
            return None
        existing_note = self._step_index_to_cached_note.get(self._held_step_index)
        if existing_note is None:
            return self._default_velocity
        return existing_note["velocity"]

    # ---- clip binding -------------------------------------------------------------------

    def set_clip(self, clip):
        """Bind to a new clip (or None). Re-registers Live-API listeners and repaints."""
        if liveobj_valid(clip):
            self._clip = clip
        else:
            self._clip = None
        self._SequencerComponent__on_clip_notes_changed.subject = self._clip
        self._SequencerComponent__on_playing_position_changed.subject = self._clip
        self._last_playhead_step_index = None
        self._rebuild_note_cache()
        self._repaint_steps()

    @listens("notes")
    def __on_clip_notes_changed(self):
        # External edit (or our own write) changed the clip: rebuild the cache and repaint.
        self._rebuild_note_cache()
        self._repaint_steps()

    @listens("playing_position")
    def __on_playing_position_changed(self):
        if not liveobj_valid(self._clip):
            return
        playhead_step_index = self._playhead_step_index()
        if playhead_step_index != self._last_playhead_step_index:
            self._last_playhead_step_index = playhead_step_index
            self._repaint_steps()

    # ---- step grid input ----------------------------------------------------------------

    @listens("value")
    def __on_step_matrix_value(self, value, column, row, is_momentary):
        # The step matrix is a 8-wide x 4-tall ButtonMatrixElement covering rows 8..5.
        # Row 0 here is the TOP grid row (note 81..88); step_index = row*8 + column.
        step_index = row * lpx_layout.GRID_SIDE_LENGTH_IN_PADS + column
        is_press = value > 0
        if is_press:
            self._on_step_pressed(step_index)
        else:
            self._on_step_released(step_index)

    def _on_step_pressed(self, step_index):
        # If a top-row hold (Length / Resolution) is active, the surface's interceptor
        # consumes this press to set length / resolution; we do not toggle a note and we do
        # NOT mark a held step (so the tuning/velocity pickers stay inactive).
        if self._step_press_interceptor is not None and self._step_press_interceptor(step_index):
            return
        # Normal tap: if the selected slot has no clip yet, ask the surface to create one
        # before drawing (so the very first step in an empty pattern creates the clip).
        if not liveobj_valid(self._clip) and self._ensure_clip_provider is not None:
            self._ensure_clip_provider()
        # Normal tap: mark the held step (enabling the tuning/velocity pickers) and toggle.
        self._held_step_index = step_index
        self._toggle_step(step_index)
        self._repaint_steps()
        # The right column is now the held step's velocity selector: tell the surface to
        # recolour it to the active state (modal feedback).
        if self._held_step_changed_callback is not None:
            self._held_step_changed_callback()

    def _on_step_released(self, step_index):
        if self._held_step_index == step_index:
            self._held_step_index = None
            self._repaint_steps()
            # No step held anymore: restore the right column's idle velocity paint.
            if self._held_step_changed_callback is not None:
                self._held_step_changed_callback()

    # ---- hold-step pickers (driven by the surface, applied to the held step) ------------

    def apply_tuning_to_held_step(self, tuning_index):
        """Set the held step's tuning: rewrite the note's pitch to the new (instrument,tuning).
        No-op (explicitly) if no step is held or there is no note at that step."""
        if self._held_step_index is None or not liveobj_valid(self._clip):
            return
        step_index = self._held_step_index
        self._tuning_per_step[step_index] = tuning_index
        existing_note = self._step_index_to_cached_note.get(step_index)
        if existing_note is None:
            return
        new_pitch = alphabase_map.note_for_instrument_and_tuning(
            self._selected_instrument_index, tuning_index
        )
        self._rewrite_note_pitch(existing_note, new_pitch)

    def apply_velocity_to_held_step(self, velocity):
        """Set the held step's velocity. If no step is held, set the default for new steps."""
        if self._held_step_index is None:
            self._default_velocity = velocity
            return
        if not liveobj_valid(self._clip):
            return
        existing_note = self._step_index_to_cached_note.get(self._held_step_index)
        if existing_note is None:
            return
        self._rewrite_note_velocity(existing_note, velocity)

    # ---- pattern operations (called by the surface's top-row buttons) -------------------

    def nudge_lane(self, step_offset):
        """Rotate the selected instrument's lane by step_offset steps (wraps within the loop)."""
        if not liveobj_valid(self._clip):
            return
        loop_length = self._loop_length_in_steps
        rotated = {}
        for step_index, note_dict in self._step_index_to_cached_note.items():
            if step_index >= loop_length:
                rotated[step_index] = note_dict  # leave notes beyond the loop untouched
                continue
            rotated[(step_index + step_offset) % loop_length] = note_dict
        # Remove the lane's notes then re-add them at their rotated times.
        self._clear_selected_instrument_lane()
        notes_to_add = []
        for step_index, note_dict in rotated.items():
            notes_to_add.append(self._make_note_specification(
                pitch=note_dict["pitch"],
                step_index=step_index,
                velocity=note_dict["velocity"],
            ))
        if notes_to_add:
            self._clip.add_new_notes(tuple(notes_to_add))

    def set_loop_length_in_steps(self, loop_length_in_steps):
        self._loop_length_in_steps = loop_length_in_steps
        self._repaint_steps()

    @property
    def loop_length_in_steps(self):
        return self._loop_length_in_steps

    # ---- note read/write against the Live clip ------------------------------------------

    def _selected_instrument_notes(self):
        """All notes in the clip whose pitch belongs to the selected instrument (any tuning)."""
        if not liveobj_valid(self._clip):
            return ()
        lowest_pitch = alphabase_map.note_for_instrument_and_tuning(
            self._selected_instrument_index, 0
        )
        pitch_span = alphabase_map.ALPHABASE_TUNINGS_PER_INSTRUMENT
        clip_length_in_beats = self._step_resolution_in_beats * lpx_layout.STEP_COUNT
        return self._clip.get_notes_extended(
            lowest_pitch, pitch_span, 0.0, clip_length_in_beats
        )

    def _rebuild_note_cache(self):
        """Snapshot the selected instrument's notes into {step_index: note_dict}."""
        self._step_index_to_cached_note = {}
        for live_note in self._selected_instrument_notes():
            step_index = self._step_index_for_time(live_note.start_time)
            if step_index is None:
                continue
            self._step_index_to_cached_note[step_index] = {
                "note_id": live_note.note_id,
                "pitch": live_note.pitch,
                "start_time": live_note.start_time,
                "duration": live_note.duration,
                "velocity": live_note.velocity,
                "mute": live_note.mute,
            }

    def _toggle_step(self, step_index):
        if not liveobj_valid(self._clip):
            return
        if step_index in self._step_index_to_cached_note:
            self._remove_step_note(step_index)
        else:
            self._add_step_note(step_index)

    def _add_step_note(self, step_index):
        tuning_index = self._tuning_per_step[step_index]
        pitch = alphabase_map.note_for_instrument_and_tuning(
            self._selected_instrument_index, tuning_index
        )
        note_specification = self._make_note_specification(
            pitch=pitch, step_index=step_index, velocity=self._default_velocity
        )
        self._clip.add_new_notes((note_specification,))

    def _remove_step_note(self, step_index):
        # remove_notes_extended deletes by pitch/time range. Target exactly this step's pitch
        # and a one-step time window so we never delete an adjacent or unrelated note.
        note_dict = self._step_index_to_cached_note[step_index]
        pitch = note_dict["pitch"]
        time_window_start = self._time_for_step(step_index)
        self._clip.remove_notes_extended(
            pitch, 1, time_window_start, self._step_resolution_in_beats
        )

    def _rewrite_note_pitch(self, note_dict, new_pitch):
        # Modify in place via get_notes_extended/apply_note_modifications, matched by note_id.
        live_notes = self._selected_instrument_notes()
        for live_note in live_notes:
            if live_note.note_id == note_dict["note_id"]:
                live_note.pitch = new_pitch
                self._clip.apply_note_modifications(live_notes)
                return

    def _rewrite_note_velocity(self, note_dict, new_velocity):
        live_notes = self._selected_instrument_notes()
        for live_note in live_notes:
            if live_note.note_id == note_dict["note_id"]:
                live_note.velocity = new_velocity
                self._clip.apply_note_modifications(live_notes)
                return

    def _clear_selected_instrument_lane(self):
        lowest_pitch = alphabase_map.note_for_instrument_and_tuning(
            self._selected_instrument_index, 0
        )
        pitch_span = alphabase_map.ALPHABASE_TUNINGS_PER_INSTRUMENT
        clip_length_in_beats = self._step_resolution_in_beats * lpx_layout.STEP_COUNT
        self._clip.remove_notes_extended(lowest_pitch, pitch_span, 0.0, clip_length_in_beats)

    def _make_note_specification(self, pitch, step_index, velocity):
        return Live.Clip.MidiNoteSpecification(
            pitch=pitch,
            start_time=self._time_for_step(step_index),
            duration=self._step_resolution_in_beats * NEW_NOTE_DURATION_AS_FRACTION_OF_STEP,
            velocity=velocity,
            mute=False,
        )

    # ---- time <-> step mapping ----------------------------------------------------------

    def _time_for_step(self, step_index):
        return step_index * self._step_resolution_in_beats

    def _step_index_for_time(self, start_time_in_beats):
        """Round a note's start_time to the nearest step, or None if it doesn't land on one."""
        approximate_step = start_time_in_beats / self._step_resolution_in_beats
        nearest_step = int(round(approximate_step))
        landed_time = nearest_step * self._step_resolution_in_beats
        if abs(landed_time - start_time_in_beats) > NOTE_TIME_MATCH_TOLERANCE_IN_BEATS:
            return None
        if not (0 <= nearest_step < lpx_layout.STEP_COUNT):
            return None
        return nearest_step

    def _playhead_step_index(self):
        if not liveobj_valid(self._clip):
            return None
        loop_window_in_beats = self._step_resolution_in_beats * self._loop_length_in_steps
        if loop_window_in_beats <= 0:
            return None
        position_within_loop = self._clip.playing_position % loop_window_in_beats
        step_index = int(position_within_loop / self._step_resolution_in_beats)
        if not (0 <= step_index < lpx_layout.STEP_COUNT):
            return None
        return step_index

    # ---- LED drawing --------------------------------------------------------------------

    def _repaint_steps(self):
        if self._led_painter is None:
            return
        playhead_step_index = (
            self._playhead_step_index() if liveobj_valid(self._clip) else None
        )
        self._led_painter.paint_step_area(
            step_index_to_cached_note=self._step_index_to_cached_note,
            tuning_per_step=self._tuning_per_step,
            playhead_step_index=playhead_step_index,
            loop_length_in_steps=self._loop_length_in_steps,
            held_step_index=self._held_step_index,
        )

    def update(self):
        super(SequencerComponent, self).update()
        if self.is_enabled():
            self._repaint_steps()
