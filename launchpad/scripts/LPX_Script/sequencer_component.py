# -*- coding: utf-8 -*-
"""32-step lane editor for one drum voice in the selected pattern clip (drum page, rows 8..5).

  - a lane is the voice's note set: the editor writes voice.note and reads
    {voice.note} | voice.also_matches; nudge, clear and velocity act on that same set;
  - tap a step = toggle it (remove every lane note on that step, or add voice.note);
  - hold a step = the right column edits that step's velocity (drum_page paints/handles it);
  - the playhead cell is repainted only when it moves to a different step;
  - while Length / Resolution is held (drum_page), the step area shows that overlay and a
    step press is consumed by drum_page's interceptor instead of toggling.

Imports Live, so it only runs inside Ableton. Every LED goes through LedPainter.
"""

from __future__ import absolute_import, print_function, unicode_literals

import logging
from collections import namedtuple

import Live
from ableton.v2.base import listens, liveobj_valid
from ableton.v2.control_surface import Component

from . import layout
from . import palette

logger = logging.getLogger(__name__)

# The six step resolutions, (label, beats per step). Default 1/16 (docs/drums.md).
RESOLUTION_OPTIONS_LABEL_AND_BEATS = (
    ("1/4", 1.0),
    ("1/8", 0.5),
    ("1/16", 0.25),
    ("1/32", 0.125),
    ("1/8T", 0.5 * 2.0 / 3.0),
    ("1/16T", 0.25 * 2.0 / 3.0),
)
DEFAULT_RESOLUTION_OPTION_INDEX = 2

NEW_NOTE_DURATION_AS_FRACTION_OF_STEP = 0.5
# A clip created by the first step drawn into an empty slot spans the whole step area.
CREATED_CLIP_LENGTH_IN_STEPS = layout.STEP_COUNT
DEFAULT_STEP_VELOCITY = 100
# Right column, bottom -> top.
VELOCITY_LEVELS_LOW_TO_HIGH = (16, 32, 48, 64, 80, 100, 114, 127)
NOTE_TIME_MATCH_TOLERANCE_IN_BEATS = 1.0e-4

STEP_OVERLAY_NONE = "none"
STEP_OVERLAY_LENGTH = "length"
STEP_OVERLAY_RESOLUTION = "resolution"


# What the step cache keeps of a Live note (copied out, never a live reference).
CachedLaneNote = namedtuple("CachedLaneNote", ("note_id", "velocity"))


def velocity_level_index_for_velocity(velocity):
    """The right-column level (0 = bottom) closest to a 0..127 velocity."""
    return min(
        range(len(VELOCITY_LEVELS_LOW_TO_HIGH)),
        key=lambda level_index: abs(VELOCITY_LEVELS_LOW_TO_HIGH[level_index] - velocity),
    )


class SequencerComponent(Component):

    def __init__(self, led_painter=None, *a, **k):
        super(SequencerComponent, self).__init__(*a, **k)
        if led_painter is None:
            raise ValueError("SequencerComponent needs led_painter")
        self._led_painter = led_painter
        self._clip = None
        self._voice = None
        self._default_velocity = DEFAULT_STEP_VELOCITY
        self._resolution_option_index = DEFAULT_RESOLUTION_OPTION_INDEX
        self._step_overlay = STEP_OVERLAY_NONE
        self._held_step_index = None
        self._last_playhead_step_index = None
        # {step_index: [CachedLaneNote, ...]} for the lane's on-grid notes (the clip stays the truth).
        self._lane_notes_by_step_index = {}

        self._step_press_interceptor = None
        self._ensure_clip_provider = None
        self._held_step_changed_callback = None

    # ---- wiring -------------------------------------------------------------------------

    def set_step_matrix(self, step_matrix):
        self._on_step_matrix_value.subject = step_matrix
        if step_matrix is None and self._held_step_index is not None:
            self._held_step_index = None  # released by the Layer mid-hold
            self._notify_held_step_changed()

    def set_step_press_interceptor(self, step_press_interceptor):
        self._step_press_interceptor = step_press_interceptor

    def set_ensure_clip_provider(self, ensure_clip_provider):
        self._ensure_clip_provider = ensure_clip_provider

    def set_held_step_changed_callback(self, held_step_changed_callback):
        self._held_step_changed_callback = held_step_changed_callback

    # ---- context ------------------------------------------------------------------------

    def set_voice(self, voice):
        """The DrumMap voice whose lane is edited, or None (no drum map: nothing to edit)."""
        self._voice = voice
        self._rebuild_lane_cache()
        self.repaint_steps()

    def set_clip(self, clip):
        self._clip = clip if liveobj_valid(clip) else None
        self._on_clip_notes_changed.subject = self._clip
        self._on_playing_position_changed.subject = self._clip
        self._on_clip_loop_start_changed.subject = self._clip
        self._on_clip_loop_end_changed.subject = self._clip
        self._last_playhead_step_index = None
        self._rebuild_lane_cache()
        self.repaint_steps()

    @property
    def clip(self):
        return self._clip

    @property
    def resolution_option_index(self):
        return self._resolution_option_index

    def set_resolution_option_index(self, resolution_option_index):
        if not (0 <= resolution_option_index < len(RESOLUTION_OPTIONS_LABEL_AND_BEATS)):
            raise ValueError("resolution option {0} out of range".format(resolution_option_index))
        self._resolution_option_index = resolution_option_index
        self._last_playhead_step_index = None
        self._rebuild_lane_cache()
        self.repaint_steps()

    @property
    def step_resolution_in_beats(self):
        return RESOLUTION_OPTIONS_LABEL_AND_BEATS[self._resolution_option_index][1]

    def loop_length_in_steps(self):
        """The bound clip's loop length in steps at the current resolution (may exceed 32).
        With no clip: the length the first drawn step will create. There is no script-side
        loop window; the clip's loop is the only one."""
        if self._clip is None:
            return CREATED_CLIP_LENGTH_IN_STEPS
        loop_length_in_beats = self._clip.loop_end - self._clip.loop_start
        return max(1, int(round(loop_length_in_beats / self.step_resolution_in_beats)))

    def set_clip_loop_length_in_steps(self, loop_length_in_steps):
        """Length hold + step: loop_end = loop_start + steps x resolution. The end marker is
        moved out first when the loop grows past it (loop_end may not pass the end marker)."""
        if not (1 <= loop_length_in_steps <= layout.STEP_COUNT):
            raise ValueError("loop length {0} out of 1..32".format(loop_length_in_steps))
        if self._clip is None:
            raise RuntimeError("set_clip_loop_length_in_steps needs a bound clip; drum_page ensures one")
        if self._clip.loop_start != 0.0:
            logger.warning("LPX Script drums: clip %r loop starts at %s, steps assume 0",
                           self._clip.name, self._clip.loop_start)
        new_loop_end = self._clip.loop_start + loop_length_in_steps * self.step_resolution_in_beats
        if new_loop_end > self._clip.end_marker:
            self._clip.end_marker = new_loop_end
        self._clip.loop_end = new_loop_end
        # loop_end's listener repaints.

    def set_step_overlay(self, step_overlay):
        if step_overlay not in (STEP_OVERLAY_NONE, STEP_OVERLAY_LENGTH, STEP_OVERLAY_RESOLUTION):
            raise ValueError("unknown step overlay {0!r}".format(step_overlay))
        self._step_overlay = step_overlay
        self.repaint_steps()

    @property
    def held_step_index(self):
        return self._held_step_index

    @property
    def default_velocity(self):
        return self._default_velocity

    def velocity_of_held_step(self):
        """The held step's (loudest) velocity, the default velocity for an empty held step,
        or None when no step is held."""
        if self._held_step_index is None:
            return None
        step_notes = self._lane_notes_by_step_index.get(self._held_step_index)
        if not step_notes:
            return self._default_velocity
        return max(note.velocity for note in step_notes)

    # ---- Live listeners -----------------------------------------------------------------

    @listens("notes")
    def _on_clip_notes_changed(self):
        self._rebuild_lane_cache()
        self.repaint_steps()

    @listens("loop_start")
    def _on_clip_loop_start_changed(self):
        self._last_playhead_step_index = None
        self.repaint_steps()

    @listens("loop_end")
    def _on_clip_loop_end_changed(self):
        self._last_playhead_step_index = None
        self.repaint_steps()

    @listens("playing_position")
    def _on_playing_position_changed(self):
        playhead_step_index = self._playhead_step_index()
        if playhead_step_index != self._last_playhead_step_index:
            self._last_playhead_step_index = playhead_step_index
            self.repaint_steps()

    # ---- step input ---------------------------------------------------------------------

    @listens("value")
    def _on_step_matrix_value(self, value, column_index, row_index, _is_momentary):
        step_index = row_index * layout.GRID_SIDE_LENGTH_IN_PADS + column_index
        if value > 0:
            self._on_step_pressed(step_index)
        else:
            self._on_step_released(step_index)

    def _on_step_pressed(self, step_index):
        if self._step_press_interceptor is not None and self._step_press_interceptor(step_index):
            return
        if self._voice is None:
            raise RuntimeError("step press reached the sequencer with no voice; drum_page must intercept")
        if self._clip is None:
            self._ensure_clip_provider()
            if self._clip is None:
                return  # drum_page logged why no clip could be created
        self._held_step_index = step_index
        self._toggle_step(step_index)
        self.repaint_steps()
        self._notify_held_step_changed()

    def _on_step_released(self, step_index):
        if self._held_step_index == step_index:
            self._held_step_index = None
            self.repaint_steps()
            self._notify_held_step_changed()

    def _notify_held_step_changed(self):
        if self._held_step_changed_callback is not None:
            self._held_step_changed_callback()

    # ---- edits --------------------------------------------------------------------------

    def apply_velocity_to_held_step(self, velocity):
        """Held step: set every lane note on it to `velocity`. No held step: new-step default."""
        if self._held_step_index is None:
            self._default_velocity = velocity
            return
        step_notes = self._lane_notes_by_step_index.get(self._held_step_index)
        if not step_notes:
            self._default_velocity = velocity
            return
        self._modify_lane_notes(
            {note.note_id for note in step_notes},
            lambda live_note: setattr(live_note, "velocity", velocity),
        )

    def nudge_lane(self, step_offset):
        """Rotate the lane's on-grid notes inside the loop by step_offset steps (wraps).
        Pitch, velocity and duration are kept; notes past the loop end are untouched."""
        if self._clip is None or self._voice is None:
            logger.info("LPX Script drums: nothing to nudge (no clip or no voice)")
            return
        loop_length = self.loop_length_in_steps()
        if loop_length > layout.STEP_COUNT:
            logger.warning("LPX Script drums: nudge refused, the clip loop (%d steps) is longer "
                           "than the 32 steps shown", loop_length)
            return
        new_start_time_by_note_id = {}
        for step_index, step_notes in self._lane_notes_by_step_index.items():
            if step_index >= loop_length:
                continue
            new_step_index = (step_index + step_offset) % loop_length
            for note in step_notes:
                new_start_time_by_note_id[note.note_id] = self._time_for_step(new_step_index)
        self._modify_lane_notes(
            set(new_start_time_by_note_id),
            lambda live_note: setattr(live_note, "start_time", new_start_time_by_note_id[live_note.note_id]),
        )

    def clear_lane(self, voice):
        """Remove every note of `voice`'s lane inside the 32-step window of the current clip."""
        if self._clip is None:
            logger.info("LPX Script drums: nothing to clear, the selected pattern slot is empty")
            return
        lane_note_ids = [live_note.note_id for live_note in self._read_lane_notes(voice)]
        if lane_note_ids:
            self._clip.remove_notes_by_id(lane_note_ids)

    def _toggle_step(self, step_index):
        step_notes = self._lane_notes_by_step_index.get(step_index)
        if step_notes:
            self._clip.remove_notes_by_id([note.note_id for note in step_notes])
        else:
            self._clip.add_new_notes((Live.Clip.MidiNoteSpecification(
                pitch=self._voice.note,
                start_time=self._time_for_step(step_index),
                duration=self.step_resolution_in_beats * NEW_NOTE_DURATION_AS_FRACTION_OF_STEP,
                velocity=self._default_velocity,
                mute=False,
            ),))

    def _modify_lane_notes(self, note_ids_to_modify, modify_live_note):
        if not note_ids_to_modify:
            return
        # The whole MidiNoteVector goes back (apply_note_modifications takes the vector as
        # returned); notes outside the lane pass through unchanged.
        live_note_vector = self._read_note_vector_covering_lane(self._voice)
        for live_note in live_note_vector:
            if live_note.note_id in note_ids_to_modify:
                modify_live_note(live_note)
        self._clip.apply_note_modifications(live_note_vector)

    # ---- reading ------------------------------------------------------------------------

    def _read_note_vector_covering_lane(self, voice):
        """Live's MidiNoteVector for the contiguous pitch range spanning `voice`'s lane over
        the 32-step window. It can contain other voices' notes (e.g. CP 39 inside SD 38/40)."""
        lowest_pitch = min(voice.lane_notes)
        pitch_span = max(voice.lane_notes) - lowest_pitch + 1
        window_in_beats = self.step_resolution_in_beats * layout.STEP_COUNT
        return self._clip.get_notes_extended(lowest_pitch, pitch_span, 0.0, window_in_beats)

    def _read_lane_notes(self, voice):
        """Only `voice`'s lane notes in the 32-step window."""
        return [
            live_note for live_note in self._read_note_vector_covering_lane(voice)
            if live_note.pitch in voice.lane_notes
        ]

    def _rebuild_lane_cache(self):
        self._lane_notes_by_step_index = {}
        if self._clip is None or self._voice is None:
            return
        for live_note in self._read_lane_notes(self._voice):
            step_index = self._step_index_for_time(live_note.start_time)
            if step_index is not None:
                self._lane_notes_by_step_index.setdefault(step_index, []).append(
                    CachedLaneNote(note_id=live_note.note_id, velocity=live_note.velocity))

    def _time_for_step(self, step_index):
        return step_index * self.step_resolution_in_beats

    def _step_index_for_time(self, start_time_in_beats):
        nearest_step = int(round(start_time_in_beats / self.step_resolution_in_beats))
        if abs(nearest_step * self.step_resolution_in_beats - start_time_in_beats) > NOTE_TIME_MATCH_TOLERANCE_IN_BEATS:
            return None  # off-grid note: it plays, but is not shown or edited
        if not (0 <= nearest_step < layout.STEP_COUNT):
            return None
        return nearest_step

    def _playhead_step_index(self):
        if self._clip is None or not self._clip.is_playing:
            return None
        # playing_position is clip time inside the clip's own loop, same axis as the steps.
        playhead_step_index = int(self._clip.playing_position / self.step_resolution_in_beats)
        if not (0 <= playhead_step_index < layout.STEP_COUNT):
            return None
        return playhead_step_index

    # ---- LEDs ---------------------------------------------------------------------------

    def _step_colour(self, step_index, playhead_step_index, loop_length_in_steps):
        if self._step_overlay == STEP_OVERLAY_LENGTH:
            if step_index == loop_length_in_steps - 1:
                return palette.DRUM_LENGTH_LOOP_END
            if step_index < loop_length_in_steps:
                return palette.DRUM_LENGTH_INSIDE_LOOP
            return palette.DRUM_LENGTH_OUTSIDE_LOOP
        if self._step_overlay == STEP_OVERLAY_RESOLUTION:
            if step_index >= len(RESOLUTION_OPTIONS_LABEL_AND_BEATS):
                return palette.OFF
            if step_index == self._resolution_option_index:
                return palette.DRUM_RESOLUTION_OPTION_SELECTED
            return palette.DRUM_RESOLUTION_OPTION
        step_notes = self._lane_notes_by_step_index.get(step_index)
        is_under_playhead = step_index == playhead_step_index
        if step_notes:
            if is_under_playhead:
                return palette.DRUM_FILLED_STEP_UNDER_PLAYHEAD
            loudest_velocity = max(note.velocity for note in step_notes)
            return palette.DRUM_STEP_FILLED_BY_VELOCITY_BAND[
                palette.drum_velocity_band_index(max(1, int(round(loudest_velocity))))]
        if is_under_playhead:
            return palette.DRUM_PLAYHEAD
        if step_index >= loop_length_in_steps:
            return palette.OFF
        return palette.DRUM_STEP_EMPTY_INSIDE_LOOP

    def repaint_steps(self):
        if not self.is_enabled():
            return  # a disabled page never paints; drum_page.repaint_page() runs on entry
        playhead_step_index = self._playhead_step_index()
        loop_length_in_steps = self.loop_length_in_steps()
        self._led_painter.paint([
            (grid_note, self._step_colour(step_index, playhead_step_index, loop_length_in_steps))
            for step_index, grid_note in enumerate(layout.STEP_INDEX_TO_GRID_NOTE)
        ])
