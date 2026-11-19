# -*- coding: utf-8 -*-
"""Drum page coordinator (launchpad/docs/drums.md).

  rows 8..5          32-step lane of the selected voice          (SequencerComponent)
  rows 4..1 cols 1-4 voice select, labelled by the DrumMap        (VoiceSelectComponent)
  rows 4..1 cols 5-8 pattern select = first 16 clip slots         (PatternSelectComponent)
  right column       velocity, 8 levels (held step, else default for new steps)
  up (hold)          Length: tap a step = the bound clip's loop ends after that step
  down (hold)        Resolution: tap one of the first 6 steps = 1/4 1/8 1/16 1/32 1/8T 1/16T
  left / right       nudge the lane one step
  super + pattern    duplicate the current pattern into that slot
  super + voice      clear that voice's lane in the current pattern

The target track comes through one seam, `track_binding.current_track()`, which follows
song.view.selected_track (read only, never changed). The DrumMap is resolved from that
track's devices; with no match every drum control does nothing, the voice pads show the error
colour and the press is logged.
"""

from __future__ import absolute_import, print_function, unicode_literals

import logging

from ableton.v2.base import listens, liveobj_valid
from ableton.v2.control_surface import Component

from . import layout
from . import palette
from .drum_maps import find_drum_map_for_track
from .pattern_select import PatternSelectComponent
from .sequencer_component import (
    CREATED_CLIP_LENGTH_IN_STEPS,
    RESOLUTION_OPTIONS_LABEL_AND_BEATS,
    STEP_OVERLAY_LENGTH,
    STEP_OVERLAY_NONE,
    STEP_OVERLAY_RESOLUTION,
    VELOCITY_LEVELS_LOW_TO_HIGH,
    SequencerComponent,
    velocity_level_index_for_velocity,
)
from .voice_select import VoiceSelectComponent

logger = logging.getLogger(__name__)

VELOCITY_LEVEL_COUNT = len(VELOCITY_LEVELS_LOW_TO_HIGH)


class SelectedTrackBinding(Component):
    """The drum page's target track: Live's selected track. The one place that decides it,
    so a second Launchpad can later bind to something else without touching the page."""

    __events__ = ("bound_track",)

    def __init__(self, *a, **k):
        super(SelectedTrackBinding, self).__init__(*a, **k)
        self._on_selected_track_changed.subject = self.song.view

    def current_track(self):
        selected_track = self.song.view.selected_track
        return selected_track if liveobj_valid(selected_track) else None

    @listens("selected_track")
    def _on_selected_track_changed(self):
        self.notify_bound_track()


class DrumPageComponent(Component):

    def __init__(self, led_painter=None, global_controls=None, *a, **k):
        super(DrumPageComponent, self).__init__(*a, **k)
        if led_painter is None or global_controls is None:
            raise ValueError("DrumPageComponent needs led_painter and global_controls")
        self._led_painter = led_painter
        self._global_controls = global_controls
        is_super_held = lambda: global_controls.super_held

        self.track_binding = SelectedTrackBinding(name="Drum_Track_Binding")
        self.sequencer = SequencerComponent(led_painter=led_painter, name="Drum_Sequencer", is_enabled=False)
        self.voice_select = VoiceSelectComponent(
            led_painter=led_painter, is_super_held=is_super_held, name="Drum_Voice_Select", is_enabled=False)
        self.pattern_select = PatternSelectComponent(
            led_painter=led_painter, is_super_held=is_super_held, name="Drum_Pattern_Select", is_enabled=False)

        self.sequencer.set_step_press_interceptor(self._intercept_step_press)
        self.sequencer.set_ensure_clip_provider(self._ensure_clip_for_selected_pattern)
        self.sequencer.set_held_step_changed_callback(self._repaint_velocity_column)
        self.voice_select.set_callbacks(
            on_voice_selected=self.sequencer.set_voice,
            voice_press_interceptor=self._intercept_voice_press,
        )
        self.pattern_select.set_callbacks(
            on_pattern_selected=self._on_pattern_selected,
            pattern_press_interceptor=self._intercept_pattern_press,
        )

        self._track = None
        self._is_length_button_held = False
        self._is_resolution_button_held = False

        self._on_bound_track_changed.subject = self.track_binding
        self._on_super_held_changed.subject = global_controls
        self._bind_target_track()

    # ---- element setters (Layer) --------------------------------------------------------

    def set_velocity_matrix(self, matrix):
        self._on_velocity_matrix_value.subject = matrix

    def set_length_button(self, button):
        self._on_length_button_value.subject = button
        if button is None and self._is_length_button_held:
            self._set_length_held(False)

    def set_resolution_button(self, button):
        self._on_resolution_button_value.subject = button
        if button is None and self._is_resolution_button_held:
            self._set_resolution_held(False)

    def set_nudge_left_button(self, button):
        self._on_nudge_left_button_value.subject = button

    def set_nudge_right_button(self, button):
        self._on_nudge_right_button_value.subject = button

    # ---- target track / drum map / clip binding -----------------------------------------

    @listens("bound_track")
    def _on_bound_track_changed(self):
        self._bind_target_track()

    @listens("devices")
    def _on_target_track_devices_changed(self):
        self._resolve_drum_map()

    def _bind_target_track(self):
        self._track = self.track_binding.current_track()
        self._on_target_track_devices_changed.subject = self._track
        self.pattern_select.set_track(self._track)
        self._resolve_drum_map()
        self._bind_selected_pattern_clip()

    def _resolve_drum_map(self):
        drum_map = find_drum_map_for_track(self._track) if self._track is not None else None
        if drum_map is None:
            logger.warning(
                "LPX Script drums: no drum map for track %r (devices: %s); drum controls are off",
                self._track.name if self._track is not None else None,
                [device.name for device in self._track.devices] if self._track is not None else [],
            )
        else:
            logger.info("LPX Script drums: track %r uses the %s map", self._track.name, drum_map.name)
        self.voice_select.set_drum_map(drum_map)
        self.sequencer.set_voice(self.voice_select.selected_voice)

    def _selected_clip_slot(self):
        if self._track is None:
            return None
        clip_slots = self.pattern_select.clip_slots_in_pattern_range()
        slot_index = self.pattern_select.selected_pattern_slot_index
        if slot_index >= len(clip_slots):
            return None
        return clip_slots[slot_index]

    def _bind_selected_pattern_clip(self):
        clip_slot = self._selected_clip_slot()
        self.sequencer.set_clip(clip_slot.clip if clip_slot is not None and clip_slot.has_clip else None)

    def _on_pattern_selected(self, _pattern_slot_index):
        self._bind_selected_pattern_clip()

    def _ensure_clip_for_selected_pattern(self):
        clip_slot = self._selected_clip_slot()
        if clip_slot is None:
            logger.warning("LPX Script drums: pattern slot %d does not exist on track %r",
                           self.pattern_select.selected_pattern_slot_index,
                           self._track.name if self._track is not None else None)
            return
        if not self._track.has_midi_input:
            logger.warning("LPX Script drums: track %r is not a MIDI track, cannot create a pattern",
                           self._track.name)
            return
        if not clip_slot.has_clip:
            clip_slot.create_clip(self.sequencer.step_resolution_in_beats * CREATED_CLIP_LENGTH_IN_STEPS)
        self.sequencer.set_clip(clip_slot.clip)

    # ---- press interception: no map / super / Length / Resolution -----------------------

    def _drum_controls_are_off(self, what_was_pressed):
        if self.voice_select.drum_map is None:
            logger.warning("LPX Script drums: %s ignored, no drum map on the target track", what_was_pressed)
            return True
        return False

    def _intercept_step_press(self, step_index):
        if self._drum_controls_are_off("step press"):
            return True
        if self._is_length_button_held:
            if self.sequencer.clip is None:
                self._ensure_clip_for_selected_pattern()
                if self.sequencer.clip is None:
                    return True  # _ensure_clip_for_selected_pattern logged why
            self.sequencer.set_clip_loop_length_in_steps(step_index + 1)
            return True
        if self._is_resolution_button_held:
            if step_index < len(RESOLUTION_OPTIONS_LABEL_AND_BEATS):
                self.sequencer.set_resolution_option_index(step_index)
            return True  # a non-option pad under the overlay never toggles a note
        if self.voice_select.selected_voice is None:
            raise RuntimeError("drum map present but no voice selected")
        return False

    def _intercept_voice_press(self, pad_index):
        if self._drum_controls_are_off("voice press"):
            return True
        if not self._global_controls.super_held:
            return False
        voice = self.voice_select.voice_at_pad_index(pad_index)
        if voice is None:
            return True  # unused pad
        logger.info("LPX Script drums: super clear lane %s", voice.name)
        self.sequencer.clear_lane(voice)
        return True

    def _intercept_pattern_press(self, pattern_slot_index):
        if self._drum_controls_are_off("pattern press"):
            return True
        if not self._global_controls.super_held:
            return False
        self._duplicate_current_pattern_to(pattern_slot_index)
        return True

    def _duplicate_current_pattern_to(self, destination_slot_index):
        clip_slots = self.pattern_select.clip_slots_in_pattern_range()
        source_slot_index = self.pattern_select.selected_pattern_slot_index
        if destination_slot_index == source_slot_index:
            logger.info("LPX Script drums: super + the selected pattern is a no-op (source = target)")
            return
        if source_slot_index >= len(clip_slots) or destination_slot_index >= len(clip_slots):
            logger.warning("LPX Script drums: duplicate %d -> %d, slot missing on the track",
                           source_slot_index, destination_slot_index)
            return
        source_slot = clip_slots[source_slot_index]
        if not source_slot.has_clip:
            logger.warning("LPX Script drums: duplicate from slot %d, which is empty", source_slot_index)
            return
        source_slot.duplicate_clip_to(clip_slots[destination_slot_index])
        logger.info("LPX Script drums: duplicated pattern %d -> %d", source_slot_index, destination_slot_index)

    # ---- round buttons ------------------------------------------------------------------

    @listens("value")
    def _on_length_button_value(self, value):
        self._set_length_held(value > 0)

    @listens("value")
    def _on_resolution_button_value(self, value):
        self._set_resolution_held(value > 0)

    def _set_length_held(self, is_held):
        self._is_length_button_held = is_held
        self._apply_step_overlay()

    def _set_resolution_held(self, is_held):
        self._is_resolution_button_held = is_held
        self._apply_step_overlay()

    def _apply_step_overlay(self):
        if self._is_length_button_held:
            self.sequencer.set_step_overlay(STEP_OVERLAY_LENGTH)
        elif self._is_resolution_button_held:
            self.sequencer.set_step_overlay(STEP_OVERLAY_RESOLUTION)
        else:
            self.sequencer.set_step_overlay(STEP_OVERLAY_NONE)
        self._repaint_arrows()

    @listens("value")
    def _on_nudge_left_button_value(self, value):
        if value > 0 and not self._drum_controls_are_off("nudge"):
            self.sequencer.nudge_lane(-1)

    @listens("value")
    def _on_nudge_right_button_value(self, value):
        if value > 0 and not self._drum_controls_are_off("nudge"):
            self.sequencer.nudge_lane(1)

    @listens("value")
    def _on_velocity_matrix_value(self, value, _column_index, row_index, _is_momentary):
        if value <= 0 or self._drum_controls_are_off("velocity"):
            return
        velocity_level_index = VELOCITY_LEVEL_COUNT - 1 - row_index  # row 0 = top = loudest
        self.sequencer.apply_velocity_to_held_step(VELOCITY_LEVELS_LOW_TO_HIGH[velocity_level_index])
        self._repaint_velocity_column()

    @listens("super_held")
    def _on_super_held_changed(self, _is_held):
        self.voice_select.repaint()
        self.pattern_select.repaint()

    # ---- LEDs ---------------------------------------------------------------------------

    def _repaint_velocity_column(self):
        if not self.is_enabled():
            return  # a disabled page never paints; repaint_page() runs on entry
        held_step_velocity = self.sequencer.velocity_of_held_step()
        if held_step_velocity is None:
            ramp = palette.DRUM_VELOCITY_REST_RAMP_LOW_TO_HIGH
            current_level_colour = palette.DRUM_VELOCITY_REST_CURRENT_LEVEL
            current_level_index = velocity_level_index_for_velocity(self.sequencer.default_velocity)
        else:
            ramp = palette.DRUM_VELOCITY_HELD_RAMP_LOW_TO_HIGH
            current_level_colour = palette.DRUM_VELOCITY_HELD_CURRENT_LEVEL
            current_level_index = velocity_level_index_for_velocity(held_step_velocity)
        self._led_painter.paint([
            (cc_number, current_level_colour if level_index == current_level_index else ramp[level_index])
            for level_index, cc_number in enumerate(layout.RIGHT_COLUMN_CC_NUMBERS_BOTTOM_TO_TOP)
        ])

    def _repaint_arrows(self):
        if not self.is_enabled():
            return
        self._led_painter.paint([
            (layout.ARROW_UP_CC_NUMBER, palette.DRUM_LENGTH_BUTTON_HELD
             if self._is_length_button_held else palette.DRUM_LENGTH_BUTTON_AT_REST),
            (layout.ARROW_DOWN_CC_NUMBER, palette.DRUM_RESOLUTION_BUTTON_HELD
             if self._is_resolution_button_held else palette.DRUM_RESOLUTION_BUTTON_AT_REST),
            (layout.ARROW_LEFT_CC_NUMBER, palette.DRUM_NUDGE_BUTTON),
            (layout.ARROW_RIGHT_CC_NUMBER, palette.DRUM_NUDGE_BUTTON),
        ])

    def repaint_page(self):
        """Full repaint; the surface calls it last when the page is entered."""
        self.sequencer.repaint_steps()
        self.voice_select.repaint()
        self.pattern_select.repaint()
        self._repaint_velocity_column()
        self._repaint_arrows()
