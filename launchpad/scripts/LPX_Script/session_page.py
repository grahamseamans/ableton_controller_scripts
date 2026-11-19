# -*- coding: utf-8 -*-
"""Session page: 8x8 clip launcher, scene launch on the right column, arrows move the ring.

Only SessionRingComponent is used from the framework (it tracks the offset and shows Live's
ring highlight and writes no LEDs). The v2 SessionComponent / SessionNavigationComponent
light their buttons through the Skin, which the one-LED-system rule forbids, so this page
fires, stops and moves the ring itself and paints every LED through LedPainter.

Colours: Live's own clip colours (clip.color, 24-bit RGB -> 0..127). Playing clips pulse,
triggered clips/scenes flash, recording pulses red. The animation lives in one place: a
timer on this component toggles the bright/dim phase and repaints (only changed LEDs are
sent).

Super held: super + clip pad stops that pad's track; super + scene button stops all clips.
"""

from __future__ import absolute_import, print_function, unicode_literals

import logging

from ableton.v2.base import listens, liveobj_valid, task
from ableton.v2.control_surface import Component

from . import layout
from . import palette

logger = logging.getLogger(__name__)

SESSION_RING_WIDTH_IN_TRACKS = layout.GRID_SIDE_LENGTH_IN_PADS
SESSION_RING_HEIGHT_IN_SCENES = layout.GRID_SIDE_LENGTH_IN_PADS
ANIMATION_HALF_PERIOD_IN_SECONDS = 0.25


class SessionPageComponent(Component):

    def __init__(self, led_painter=None, global_controls=None, session_ring=None, *a, **k):
        super(SessionPageComponent, self).__init__(*a, **k)
        if led_painter is None or global_controls is None or session_ring is None:
            raise ValueError("SessionPageComponent needs led_painter, global_controls and session_ring")
        self._led_painter = led_painter
        self._global_controls = global_controls
        self._session_ring = session_ring
        self._is_bright_animation_phase = True
        self._last_painted_colour_by_led_index = {}
        # Pads whose press fired a clip slot, so only those get the release (gate launch modes).
        self._fired_clip_slot_by_grid_note = {}
        self._fired_scene_by_right_column_row = {}

        self._on_super_held_changed.subject = global_controls
        self._on_session_ring_offset_changed.subject = session_ring
        self._on_session_ring_tracks_changed.subject = session_ring
        self._on_scenes_changed.subject = self.song

        self._animation_task = self._tasks.add(task.loop(
            task.wait(ANIMATION_HALF_PERIOD_IN_SECONDS),
            task.run(self._on_animation_tick),
        ))

    # ---- element setters (Layer) --------------------------------------------------------

    def set_clip_launch_matrix(self, matrix):
        self._on_clip_launch_matrix_value.subject = matrix

    def set_scene_launch_matrix(self, matrix):
        self._on_scene_launch_matrix_value.subject = matrix

    def set_up_button(self, button):
        self._on_up_button_value.subject = button

    def set_down_button(self, button):
        self._on_down_button_value.subject = button

    def set_left_button(self, button):
        self._on_left_button_value.subject = button

    def set_right_button(self, button):
        self._on_right_button_value.subject = button

    # ---- ring geometry ------------------------------------------------------------------

    def _track_for_column(self, column_index):
        tracks = self._session_ring.tracks_to_use()
        track_index = self._session_ring.track_offset + column_index
        if track_index < len(tracks):
            return tracks[track_index]
        return None

    def _scene_for_row(self, row_index):
        scenes = self._session_ring.scenes()
        scene_index = self._session_ring.scene_offset + row_index
        if scene_index < len(scenes):
            return scenes[scene_index]
        return None

    def _clip_slot_for_position(self, column_index, row_index):
        track = self._track_for_column(column_index)
        if track is None:
            return None
        scene_index = self._session_ring.scene_offset + row_index
        clip_slots = track.clip_slots
        if scene_index < len(clip_slots):
            return clip_slots[scene_index]
        return None

    def _can_move(self, direction):
        ring = self._session_ring
        if direction == "up":
            return ring.scene_offset > 0
        if direction == "down":
            return ring.scene_offset + SESSION_RING_HEIGHT_IN_SCENES < len(ring.scenes())
        if direction == "left":
            return ring.track_offset > 0
        if direction == "right":
            return ring.track_offset + SESSION_RING_WIDTH_IN_TRACKS < len(ring.tracks_to_use())
        raise ValueError("unknown direction {0!r}".format(direction))

    def _move_ring(self, direction):
        if not self._can_move(direction):
            logger.info("LPX Script session: ring cannot move %s (edge of the set)", direction)
            return
        track_step, scene_step = {
            "up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
        }[direction]
        ring = self._session_ring
        ring.set_offsets(ring.track_offset + track_step, ring.scene_offset + scene_step)

    # ---- input --------------------------------------------------------------------------

    @listens("value")
    def _on_clip_launch_matrix_value(self, value, column_index, row_index, _is_momentary):
        grid_note = layout.grid_note_for_matrix_position(column_index, row_index)
        if value > 0:
            if self._global_controls.super_held:
                self._stop_track_in_column(column_index)
                return
            clip_slot = self._clip_slot_for_position(column_index, row_index)
            if clip_slot is None:
                logger.info("LPX Script session: pad %d is outside the set (no track/scene)", grid_note)
                return
            clip_slot.set_fire_button_state(True)
            self._fired_clip_slot_by_grid_note[grid_note] = clip_slot
        else:
            clip_slot = self._fired_clip_slot_by_grid_note.pop(grid_note, None)
            if clip_slot is not None and liveobj_valid(clip_slot):
                clip_slot.set_fire_button_state(False)

    def _stop_track_in_column(self, column_index):
        track = self._track_for_column(column_index)
        if track is None:
            logger.info("LPX Script session: super-stop on column %d, which has no track", column_index)
            return
        track.stop_all_clips()

    @listens("value")
    def _on_scene_launch_matrix_value(self, value, _column_index, row_index, _is_momentary):
        if value > 0:
            if self._global_controls.super_held:
                self.song.stop_all_clips()
                return
            scene = self._scene_for_row(row_index)
            if scene is None:
                logger.info("LPX Script session: scene button %d is past the last scene", row_index)
                return
            scene.set_fire_button_state(True)
            self._fired_scene_by_right_column_row[row_index] = scene
        else:
            scene = self._fired_scene_by_right_column_row.pop(row_index, None)
            if scene is not None and liveobj_valid(scene):
                scene.set_fire_button_state(False)

    @listens("value")
    def _on_up_button_value(self, value):
        if value > 0:
            self._move_ring("up")

    @listens("value")
    def _on_down_button_value(self, value):
        if value > 0:
            self._move_ring("down")

    @listens("value")
    def _on_left_button_value(self, value):
        if value > 0:
            self._move_ring("left")

    @listens("value")
    def _on_right_button_value(self, value):
        if value > 0:
            self._move_ring("right")

    # ---- change events ------------------------------------------------------------------

    @listens("super_held")
    def _on_super_held_changed(self, _is_held):
        self._repaint_changed_leds()

    @listens("offset")
    def _on_session_ring_offset_changed(self, _track_offset, _scene_offset):
        self._repaint_changed_leds()

    @listens("tracks")
    def _on_session_ring_tracks_changed(self):
        self._repaint_changed_leds()

    @listens("scenes")
    def _on_scenes_changed(self):
        self._repaint_changed_leds()

    def _on_animation_tick(self):
        self._is_bright_animation_phase = not self._is_bright_animation_phase
        self._repaint_changed_leds()

    # ---- LEDs ---------------------------------------------------------------------------

    def _clip_pad_colour(self, track, clip_slot, super_held, track_has_playing_clip):
        if super_held and track_has_playing_clip:
            return palette.SESSION_SUPER_STOP_TARGET
        if clip_slot is None:
            return palette.OFF
        if clip_slot.has_clip:
            clip = clip_slot.clip
            if clip.is_recording:
                base_colour, animation_style = palette.SESSION_CLIP_RECORDING, palette.ANIMATION_PULSE
            elif clip.is_playing:
                base_colour, animation_style = palette.rgb_from_live_color(clip.color), palette.ANIMATION_PULSE
            elif clip.is_triggered:
                base_colour, animation_style = palette.rgb_from_live_color(clip.color), palette.ANIMATION_FLASH
            else:
                base_colour, animation_style = palette.rgb_from_live_color(clip.color), palette.ANIMATION_STATIC
            return palette.animated_colour(base_colour, animation_style, self._is_bright_animation_phase)
        track_is_armed = track.can_be_armed and (track.arm or track.implicit_arm)
        if track_is_armed:
            animation_style = palette.ANIMATION_FLASH if clip_slot.is_triggered else palette.ANIMATION_STATIC
            return palette.animated_colour(
                palette.SESSION_EMPTY_SLOT_ON_ARMED_TRACK, animation_style, self._is_bright_animation_phase)
        return palette.OFF

    def _scene_button_colour(self, scene, super_held):
        if super_held:
            return palette.SESSION_SUPER_STOP_TARGET
        if scene is None:
            return palette.OFF
        if scene.is_triggered:
            return palette.animated_colour(
                palette.SESSION_SCENE_TRIGGERED, palette.ANIMATION_FLASH, self._is_bright_animation_phase)
        if any(clip_slot.has_clip for clip_slot in scene.clip_slots):
            return palette.SESSION_SCENE_HAS_CLIPS
        return palette.OFF

    def _all_page_leds(self):
        super_held = self._global_controls.super_held
        leds = []
        for column_index in range(SESSION_RING_WIDTH_IN_TRACKS):
            track = self._track_for_column(column_index)
            track_has_playing_clip = track is not None and track.playing_slot_index >= 0
            for row_index in range(SESSION_RING_HEIGHT_IN_SCENES):
                clip_slot = self._clip_slot_for_position(column_index, row_index)
                leds.append((
                    layout.grid_note_for_matrix_position(column_index, row_index),
                    self._clip_pad_colour(track, clip_slot, super_held, track_has_playing_clip),
                ))
        for row_index, cc_number in enumerate(layout.RIGHT_COLUMN_CC_NUMBERS_TOP_TO_BOTTOM):
            leds.append((cc_number, self._scene_button_colour(self._scene_for_row(row_index), super_held)))
        for direction, cc_number in zip(("up", "down", "left", "right"), layout.ARROW_CC_NUMBERS_UP_DOWN_LEFT_RIGHT):
            leds.append((cc_number, palette.SESSION_ARROW_CAN_MOVE if self._can_move(direction) else palette.OFF))
        return leds

    def _repaint_changed_leds(self):
        if not self.is_enabled():
            return  # a disabled page never paints; repaint_page() runs on entry
        changed_leds = [
            (led_index, colour) for led_index, colour in self._all_page_leds()
            if self._last_painted_colour_by_led_index.get(led_index) != colour
        ]
        self._led_painter.paint(changed_leds)
        self._last_painted_colour_by_led_index.update(changed_leds)

    def repaint_page(self):
        """Full repaint; the surface calls it last when the page is entered."""
        self._last_painted_colour_by_led_index = {}
        self._repaint_changed_leds()

    def update(self):
        super(SessionPageComponent, self).update()
        if not self.is_enabled():
            # Forget what was on the device; the next page paints over it.
            self._last_painted_colour_by_led_index = {}
