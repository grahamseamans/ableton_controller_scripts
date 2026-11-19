# -*- coding: utf-8 -*-
"""Jomox Pattern Programmer ControlSurface for the Novation Launchpad X.

This is the top-level remote script. It:
  - puts the Launchpad X into Programmer mode on connect and reverts to Live mode on
    disconnect (so the device is never left stuck in Programmer mode),
  - builds the LPX elements (grid, top round row, right round column),
  - creates the LedPainter and the three editing components and wires them with Layers,
  - owns the top-row buttons (Copy, Paste, Length, Resolution, Preview, Solo, Nudge</>),
  - owns the right-column velocity selector and the hold gestures (Length / Resolution over
    the step area; tuning / velocity for a held step),
  - binds the sequencer to the selected pattern slot's clip and creates a clip on demand,
  - forwards preview/play-in notes to the armed track's input (Launchpad95-style).

This file imports Live/ableton and only runs inside Ableton. It mirrors the decompiled
Live 12 `ableton.v2.control_surface` idioms (ControlSurface subclass, `component_guard`,
ButtonElement/ButtonMatrixElement/SysexElement, Layer, `@listens`).

No quiet fallbacks: when there is no AlphaBase track / no clip, controls explicitly no-op.
"""

from __future__ import absolute_import, print_function, unicode_literals

import Live
from ableton.v2.base import listens, liveobj_valid
from ableton.v2.control_surface import (
    IdentifiableControlSurface,
    Layer,
    MIDI_CC_TYPE,
    MIDI_NOTE_TYPE,
)
from ableton.v2.control_surface.elements import ButtonElement, ButtonMatrixElement, SysexElement

from . import alphabase_map
from . import lpx_layout
from . import lpx_led
from .sequencer_component import (
    SequencerComponent,
    VELOCITY_LEVELS_LOW_TO_HIGH,
    DEFAULT_STEP_VELOCITY,
)


def velocity_level_index_for_velocity(velocity):
    """Map a 0..127 velocity onto the closest of the 8 selectable levels (its column index)."""
    return min(
        range(len(VELOCITY_LEVELS_LOW_TO_HIGH)),
        key=lambda level_index: abs(VELOCITY_LEVELS_LOW_TO_HIGH[level_index] - velocity),
    )
from .instrument_select import InstrumentSelectComponent
from .pattern_select import PatternSelectComponent

# The six selectable step resolutions, as (label, beats-per-step). 1/16 is the default.
# beats-per-step: a quarter note = 1.0 beat; a 1/16 = 0.25; triplets multiply by 2/3.
RESOLUTION_OPTIONS_LABEL_AND_BEATS = (
    ("1/4", 1.0),
    ("1/8", 0.5),
    ("1/16", 0.25),
    ("1/32", 0.125),
    ("1/8T", 0.5 * 2.0 / 3.0),
    ("1/16T", 0.25 * 2.0 / 3.0),
)
DEFAULT_RESOLUTION_OPTION_INDEX = 2  # 1/16

# Length of a clip the script creates on demand, in beats: 32 steps at the default resolution.
DEFAULT_CREATED_CLIP_LENGTH_IN_BEATS = 0.25 * lpx_layout.STEP_COUNT

# Velocity used for a preview/play-in note forwarded to the armed track.
PREVIEW_NOTE_VELOCITY = 110

# MIDI note message bytes for forwarding preview notes on the AlphaBase keymap channel.
NOTE_ON_STATUS_FOR_KEYMAP_CHANNEL = 0x90 + alphabase_map.ALPHABASE_KEYMAP_MIDI_CHANNEL_ZERO_BASED
NOTE_OFF_STATUS_FOR_KEYMAP_CHANNEL = 0x80 + alphabase_map.ALPHABASE_KEYMAP_MIDI_CHANNEL_ZERO_BASED


def create_button_element(identifier, message_type, name):
    return ButtonElement(True, message_type, 0, identifier, name=name)


class JomoxPatternProgrammer(IdentifiableControlSurface):
    """The Launchpad X turned into a 32-step AlphaBase pattern programmer.

    Subclasses IdentifiableControlSurface (like the decompiled `Launchpad_X`/`NovationBase`)
    so the framework runs the Universal-Device-Inquiry handshake and calls `on_identified`
    AFTER the LPX answers — which is when (and only when) it is safe to send the
    enter-Programmer-mode SysEx. Sending it from `__init__` was too early (the port/device was
    not confirmed yet)."""

    def __init__(self, *a, **k):
        super(JomoxPatternProgrammer, self).__init__(
            *a, product_id_bytes=lpx_layout.LPX_PRODUCT_ID_BYTES, **k
        )
        with self.component_guard():
            self._create_elements()
            self._led_painter = lpx_led.LedPainter(send_sysex_message=self._send_midi)
            self._create_components()
            self._wire_layers()

            # Editing state owned by the surface (it coordinates the components).
            self._selected_resolution_option_index = DEFAULT_RESOLUTION_OPTION_INDEX
            self._is_length_button_held = False
            self._is_resolution_button_held = False
            self._is_preview_enabled = False

            self._JomoxPatternProgrammer__on_selected_track_changed.subject = self.song.view
            self._bind_alphabase_track()
            self._apply_resolution_to_sequencer()
            self._bind_selected_pattern_clip(self._pattern_select.selected_pattern_slot_index)

    # ---- programmer-mode SysEx ----------------------------------------------------------
    # The mode switch is a SysexElement (matching the reference's `firmware_mode_switch`):
    # `send_value(PROGRAMMER)` / `send_value(LIVE)` emits the full F0..0E <byte>..F7 message.

    def on_identified(self, midi_bytes):
        # The LPX has answered the identity request: now it is safe to enter Programmer mode
        # and paint the initial surface state (mirrors Launchpad_X.on_identified, which sends
        # its firmware/layout mode-switch SysEx here before calling super()).
        self._firmware_mode_switch.send_value(lpx_layout.LPX_PROGRAMMER_MODE_VALUE_BYTE)
        self._repaint_top_buttons()
        # Paint the right column to its idle velocity ramp (with no step held it sets the
        # default velocity for new steps; it recolours to the active selector while a step is
        # held — see Fix 4 / the modal-feedback principle).
        self._repaint_velocity_column()
        super(JomoxPatternProgrammer, self).on_identified(midi_bytes)

    def disconnect(self):
        # Leave the device the way we found it.
        self._firmware_mode_switch.send_value(lpx_layout.LPX_LIVE_MODE_VALUE_BYTE)
        super(JomoxPatternProgrammer, self).disconnect()

    # ---- elements -----------------------------------------------------------------------

    def _create_elements(self):
        # Programmer/Live mode switch as a SysexElement (the reference's `firmware_mode_switch`
        # idiom): send_value(v) builds F0 ..header.. <command 0x0E> <v> F7. We drive it from
        # on_identified (enter Programmer) and disconnect (revert to Live).
        self._firmware_mode_switch = SysexElement(
            name="Firmware_Mode_Switch",
            send_message_generator=lambda mode_value_byte: (
                lpx_layout.LPX_SYSEX_HEADER
                + (lpx_layout.LPX_LAYOUT_MODE_COMMAND_BYTE, mode_value_byte, lpx_layout.LPX_SYSEX_END)
            ),
        )

        # The full 8x8 grid as note buttons (note = row*10 + col), addressed top row first.
        self._grid_button_by_note = {}
        grid_rows_top_to_bottom = []
        for row_number in lpx_layout.GRID_ROW_NUMBERS_TOP_TO_BOTTOM:
            row_buttons = []
            for column_number in lpx_layout.GRID_COLUMN_NUMBERS_LEFT_TO_RIGHT:
                note = lpx_layout.grid_note_for_row_and_column(row_number, column_number)
                button = create_button_element(
                    note, MIDI_NOTE_TYPE, "Grid_Pad_{0}".format(note)
                )
                self._grid_button_by_note[note] = button
                row_buttons.append(button)
            grid_rows_top_to_bottom.append(row_buttons)

        # Step-area submatrix: rows 8..5 = the first 4 rows of grid_rows_top_to_bottom.
        self._step_matrix = ButtonMatrixElement(
            rows=grid_rows_top_to_bottom[0:4], name="Step_Matrix"
        )
        # Instrument quad: rows 4..1, cols 1..4 = rows[4:8], columns 0..3.
        self._instrument_matrix = ButtonMatrixElement(
            rows=[row[0:4] for row in grid_rows_top_to_bottom[4:8]], name="Instrument_Matrix"
        )
        # Pattern quad: rows 4..1, cols 5..8 = rows[4:8], columns 4..7.
        self._pattern_matrix = ButtonMatrixElement(
            rows=[row[4:8] for row in grid_rows_top_to_bottom[4:8]], name="Pattern_Matrix"
        )

        # The 4 leftmost bottom-row pads, reused for the hold-step tuning picker.
        self._option_pad_buttons = [
            self._grid_button_by_note[note]
            for note in lpx_layout.OPTION_PAD_GRID_NOTES_LEFT_TO_RIGHT
        ]

        # Top round row buttons (CC), by semantic name.
        self._top_button_by_name = {}
        for name in lpx_layout.TOP_ROW_BUTTON_NAMES_LEFT_TO_RIGHT:
            cc_number = lpx_layout.TOP_ROW_CC_FOR_BUTTON_NAME[name]
            self._top_button_by_name[name] = create_button_element(
                cc_number, MIDI_CC_TYPE, "Top_{0}".format(name)
            )

        # Right round column buttons (CC), bottom -> top = velocity levels 0..7.
        self._right_column_buttons = [
            create_button_element(cc_number, MIDI_CC_TYPE, "Right_Velocity_{0}".format(level))
            for level, cc_number in enumerate(
                lpx_layout.RIGHT_COLUMN_CC_NUMBERS_BOTTOM_TO_TOP
            )
        ]
        self._right_column_matrix = ButtonMatrixElement(
            rows=[self._right_column_buttons], name="Velocity_Column"
        )

    # ---- components ---------------------------------------------------------------------

    def _create_components(self):
        self._sequencer = SequencerComponent(
            led_painter=self._led_painter, name="Sequencer", is_enabled=False
        )
        self._instrument_select = InstrumentSelectComponent(
            led_painter=self._led_painter, name="Instrument_Select", is_enabled=False
        )
        self._pattern_select = PatternSelectComponent(
            led_painter=self._led_painter, name="Pattern_Select", is_enabled=False
        )

        self._instrument_select.set_callbacks(
            on_instrument_selected=self._on_instrument_selected,
            request_preview=self._forward_preview_note,
            is_preview_enabled=lambda: self._is_preview_enabled,
        )
        self._pattern_select.set_callbacks(on_pattern_selected=self._bind_selected_pattern_clip)
        self._sequencer.set_step_press_interceptor(self._intercept_step_press)
        self._sequencer.set_ensure_clip_provider(self._ensure_clip_for_selected_pattern)
        self._sequencer.set_held_step_changed_callback(self._repaint_velocity_column)

        for component in (self._sequencer, self._instrument_select, self._pattern_select):
            component.set_enabled(True)

    def _wire_layers(self):
        self._sequencer.layer = Layer(step_matrix=self._step_matrix)
        self._instrument_select.layer = Layer(instrument_matrix=self._instrument_matrix)
        self._pattern_select.layer = Layer(pattern_matrix=self._pattern_matrix)

        # Top-row buttons: bind press/release listeners directly (the surface owns them).
        self._JomoxPatternProgrammer__on_copy_value.subject = (
            self._top_button_by_name[lpx_layout.TOP_ROW_BUTTON_COPY]
        )
        self._JomoxPatternProgrammer__on_paste_value.subject = (
            self._top_button_by_name[lpx_layout.TOP_ROW_BUTTON_PASTE]
        )
        self._JomoxPatternProgrammer__on_length_value.subject = (
            self._top_button_by_name[lpx_layout.TOP_ROW_BUTTON_LENGTH]
        )
        self._JomoxPatternProgrammer__on_resolution_value.subject = (
            self._top_button_by_name[lpx_layout.TOP_ROW_BUTTON_RESOLUTION]
        )
        self._JomoxPatternProgrammer__on_preview_value.subject = (
            self._top_button_by_name[lpx_layout.TOP_ROW_BUTTON_PREVIEW]
        )
        self._JomoxPatternProgrammer__on_solo_value.subject = (
            self._top_button_by_name[lpx_layout.TOP_ROW_BUTTON_SOLO]
        )
        self._JomoxPatternProgrammer__on_nudge_left_value.subject = (
            self._top_button_by_name[lpx_layout.TOP_ROW_BUTTON_NUDGE_LEFT]
        )
        self._JomoxPatternProgrammer__on_nudge_right_value.subject = (
            self._top_button_by_name[lpx_layout.TOP_ROW_BUTTON_NUDGE_RIGHT]
        )

        # Right column velocity selector and the option-pad tuning picker.
        self._JomoxPatternProgrammer__on_velocity_value.subject = self._right_column_matrix
        self._option_pad_matrix = ButtonMatrixElement(
            rows=[self._option_pad_buttons], name="Option_Pads"
        )
        self._JomoxPatternProgrammer__on_option_pad_value.subject = self._option_pad_matrix

    # ---- AlphaBase track / clip binding -------------------------------------------------

    def _alphabase_track(self):
        """The single MIDI track that carries the AlphaBase. We use the selected track; the
        one-time Live template (architecture.md) is one MIDI track -> AlphaBase Ch.16."""
        selected_track = self.song.view.selected_track
        if liveobj_valid(selected_track) and selected_track.has_midi_input:
            return selected_track
        return None

    def _bind_alphabase_track(self):
        track = self._alphabase_track()
        self._pattern_select.set_track(track)

    @listens("selected_track")
    def __on_selected_track_changed(self):
        # The AlphaBase track is whichever MIDI track is selected. Re-bind patterns + clip.
        self._bind_alphabase_track()
        self._bind_selected_pattern_clip(self._pattern_select.selected_pattern_slot_index)

    def _bind_selected_pattern_clip(self, pattern_slot_index):
        track = self._alphabase_track()
        if track is None:
            self._sequencer.set_clip(None)
            return
        clip_slots = track.clip_slots
        if pattern_slot_index >= len(clip_slots):
            self._sequencer.set_clip(None)
            return
        clip_slot = clip_slots[pattern_slot_index]
        if clip_slot.has_clip:
            self._sequencer.set_clip(clip_slot.clip)
        else:
            # No clip yet: bind to None. A clip is created on the first step draw (see below).
            self._sequencer.set_clip(None)

    def _ensure_clip_for_selected_pattern(self):
        """Create an empty clip in the selected slot if it has none, then bind to it.
        Returns the bound clip or None (when there is no track / slot)."""
        track = self._alphabase_track()
        if track is None:
            return None
        clip_slots = track.clip_slots
        pattern_slot_index = self._pattern_select.selected_pattern_slot_index
        if pattern_slot_index >= len(clip_slots):
            return None
        clip_slot = clip_slots[pattern_slot_index]
        if not clip_slot.has_clip:
            clip_slot.create_clip(DEFAULT_CREATED_CLIP_LENGTH_IN_BEATS)
        self._sequencer.set_clip(clip_slot.clip)
        return clip_slot.clip

    # ---- instrument selection -----------------------------------------------------------

    def _on_instrument_selected(self, instrument_index):
        self._sequencer.set_selected_instrument_index(instrument_index)

    # ---- resolution ---------------------------------------------------------------------

    def _apply_resolution_to_sequencer(self):
        _label, beats_per_step = RESOLUTION_OPTIONS_LABEL_AND_BEATS[
            self._selected_resolution_option_index
        ]
        self._sequencer.set_step_resolution_in_beats(beats_per_step)

    # ---- top-row button handlers --------------------------------------------------------

    @listens("value")
    def __on_copy_value(self, value):
        if value > 0:
            self._copy_current_pattern()

    @listens("value")
    def __on_paste_value(self, value):
        if value > 0:
            self._paste_into_current_pattern()

    @listens("value")
    def __on_length_value(self, value):
        self._is_length_button_held = value > 0
        if self._is_length_button_held:
            self._led_painter.paint_length_overlay(self._sequencer.loop_length_in_steps)
        else:
            self._sequencer.update()  # restore normal step painting
        self._repaint_top_buttons()

    @listens("value")
    def __on_resolution_value(self, value):
        self._is_resolution_button_held = value > 0
        if self._is_resolution_button_held:
            self._led_painter.paint_resolution_overlay(
                resolution_option_count=len(RESOLUTION_OPTIONS_LABEL_AND_BEATS),
                selected_resolution_index=self._selected_resolution_option_index,
            )
        else:
            self._sequencer.update()
        self._repaint_top_buttons()

    @listens("value")
    def __on_preview_value(self, value):
        if value > 0:
            self._is_preview_enabled = not self._is_preview_enabled
            self._repaint_top_buttons()

    @listens("value")
    def __on_solo_value(self, value):
        if value > 0:
            self._solo_selected_instrument()

    @listens("value")
    def __on_nudge_left_value(self, value):
        if value > 0:
            self._sequencer.nudge_lane(-1)

    @listens("value")
    def __on_nudge_right_value(self, value):
        if value > 0:
            self._sequencer.nudge_lane(1)

    # ---- step grid press interception for hold-Length / hold-Resolution -----------------
    # The step matrix is wired only to the sequencer. The sequencer consults this interceptor
    # on every step press: while Length or Resolution is held, the press sets the loop length
    # or picks a resolution (and is consumed) instead of toggling a note.

    def _intercept_step_press(self, step_index):
        if self._is_length_button_held:
            # Tapped step becomes the loop end: length = step_index + 1.
            self._sequencer.set_loop_length_in_steps(step_index + 1)
            self._led_painter.paint_length_overlay(self._sequencer.loop_length_in_steps)
            return True
        if self._is_resolution_button_held:
            if step_index < len(RESOLUTION_OPTIONS_LABEL_AND_BEATS):
                self._selected_resolution_option_index = step_index
                self._apply_resolution_to_sequencer()
                self._led_painter.paint_resolution_overlay(
                    resolution_option_count=len(RESOLUTION_OPTIONS_LABEL_AND_BEATS),
                    selected_resolution_index=self._selected_resolution_option_index,
                )
            return True  # consume even an out-of-range pad so it never toggles a note
        return False

    # ---- right column velocity + option-pad tuning --------------------------------------

    @listens("value")
    def __on_velocity_value(self, value, column, row, is_momentary):
        if value <= 0:
            return
        # The column matrix is 8 wide x 1 tall, bottom -> top, so the velocity level == column.
        velocity_level_index = column
        velocity = VELOCITY_LEVELS_LOW_TO_HIGH[velocity_level_index]
        self._sequencer.apply_velocity_to_held_step(velocity)
        # Recolour: active (highlighting the picked level) while a step is held, idle otherwise.
        self._repaint_velocity_column()

    def _repaint_velocity_column(self):
        """Paint the right column to its current role: the bright "velocity-selector active"
        state highlighting the held step's velocity while a step is held (modal feedback), or
        the dim idle ramp marking the default-velocity level when no step is held."""
        held_step_velocity = self._sequencer.velocity_of_held_step()
        if held_step_velocity is None:
            self._led_painter.paint_velocity_column_idle(
                velocity_level_index_for_velocity(DEFAULT_STEP_VELOCITY)
            )
        else:
            self._led_painter.paint_velocity_column_active(
                velocity_level_index_for_velocity(held_step_velocity)
            )

    @listens("value")
    def __on_option_pad_value(self, value, column, row, is_momentary):
        if value <= 0:
            return
        # Only meaningful while a step is held (tuning picker). Otherwise these are spare
        # instrument pads and we explicitly do nothing.
        if self._sequencer.held_step_index is None:
            return
        tuning_index = column
        self._sequencer.apply_tuning_to_held_step(tuning_index)
        self._led_painter.paint_tuning_picker(tuning_index)

    # ---- pattern copy / paste -----------------------------------------------------------

    def _copy_current_pattern(self):
        track = self._alphabase_track()
        if track is None:
            return
        pattern_slot_index = self._pattern_select.selected_pattern_slot_index
        clip_slots = track.clip_slots
        if pattern_slot_index >= len(clip_slots):
            return
        self._copied_from_slot_index = pattern_slot_index

    def _paste_into_current_pattern(self):
        if not hasattr(self, "_copied_from_slot_index"):
            return
        track = self._alphabase_track()
        if track is None:
            return
        clip_slots = track.clip_slots
        source_index = self._copied_from_slot_index
        destination_index = self._pattern_select.selected_pattern_slot_index
        if source_index >= len(clip_slots) or destination_index >= len(clip_slots):
            return
        source_slot = clip_slots[source_index]
        if not source_slot.has_clip:
            return
        source_slot.duplicate_clip_to(clip_slots[destination_index])
        self._bind_selected_pattern_clip(destination_index)

    # ---- solo ---------------------------------------------------------------------------

    def _solo_selected_instrument(self):
        # The AlphaBase makes the sound, not a Live device, so there is no per-instrument
        # Live object to solo. Soloing a single keymap instrument from Live is not possible
        # without device-level control; this explicitly no-ops and is flagged in SHORTCUTS.md.
        return

    # ---- preview note forwarding --------------------------------------------------------

    def _forward_preview_note(self, instrument_index):
        """Send a short keymap note to audition the instrument. The note is emitted on the
        AlphaBase keymap channel; whether Live routes the script's output to the AlphaBase
        depends on Track-input routing (see SHORTCUTS.md)."""
        note = alphabase_map.note_for_instrument_and_tuning(instrument_index, 0)
        self._send_midi((NOTE_ON_STATUS_FOR_KEYMAP_CHANNEL, note, PREVIEW_NOTE_VELOCITY))
        self._send_midi((NOTE_OFF_STATUS_FOR_KEYMAP_CHANNEL, note, 0))

    # ---- LED housekeeping ---------------------------------------------------------------

    def _repaint_top_buttons(self):
        for name, button in self._top_button_by_name.items():
            is_active = (
                (name == lpx_layout.TOP_ROW_BUTTON_LENGTH and self._is_length_button_held)
                or (name == lpx_layout.TOP_ROW_BUTTON_RESOLUTION and self._is_resolution_button_held)
                or (name == lpx_layout.TOP_ROW_BUTTON_PREVIEW and self._is_preview_enabled)
            )
            cc_number = lpx_layout.TOP_ROW_CC_FOR_BUTTON_NAME[name]
            self._led_painter.paint_top_button(cc_number, is_active)
