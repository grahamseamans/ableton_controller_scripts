# -*- coding: utf-8 -*-
"""Launchpad X batch-RGB SysEx LED painter and the documented colour palette.

The SysEx builder and palette are PURE PYTHON (no Live / ableton imports) so they can be
unit-tested with `uv run python lpx_led.py`.

Batch-RGB SysEx (knowledge_base/hardware/novation_launchpad_x/notes.md, p.12-15):

    F0 00 20 29 02 0C 03  <led-spec> <led-spec> ...  F7

Each <led-spec> is `<type> <index> <data...>`. For RGB lighting, type = 3 and data is the
three colour bytes r, g, b (each 0..127). `index` is the pad's programmer-mode note/CC
number (the same 11..88 / 91..98 / 19..89 numbers the pad emits). Up to 81 LEDs per message.

Palette design follows architecture.md "Modal feedback principle": ONE non-overlapping
colour FAMILY per function, so that pads which carry different meanings in different modes
(notably the leftmost bottom-row option pads, and the step-area pads under hold-Resolution)
are never the same colour in two different modes. Each family below is a distinct hue.
"""

from __future__ import absolute_import, print_function, unicode_literals

# lpx_layout is pure Python (no Live import), so importing it here keeps lpx_led runnable both
# as a package module inside Live (`from . import lpx_layout`) and standalone for the
# self-check (`import lpx_layout`, resolved from the same directory on sys.path). This is a
# script-vs-package shim, not a silent failure path.
try:
    from . import lpx_layout
    from . import alphabase_map
except ImportError:
    import lpx_layout
    import alphabase_map

# ----------------------------------------------------------------------------------------
# Raw SysEx framing. Single-sourced from lpx_layout (the layout module owns the LPX SysEx
# header/end constants); the painter just reuses them so there is exactly one definition.
# ----------------------------------------------------------------------------------------

LPX_SYSEX_HEADER = lpx_layout.LPX_SYSEX_HEADER
LPX_SYSEX_END = lpx_layout.LPX_SYSEX_END

# Command 03 = "lighting" / set-LED batch message.
LPX_LED_BATCH_COMMAND_BYTE = 0x03

# LED spec type 3 = RGB (r, g, b each 0..127).
LPX_LED_SPEC_TYPE_RGB = 3

# The Launchpad X accepts at most 81 LED specs in a single command-03 message.
LPX_MAX_LED_SPECS_PER_MESSAGE = 81

# A colour byte is a 7-bit value.
LED_COLOUR_BYTE_MAX = 127


def _clamp_colour_byte(value):
    """Clamp an int into the 0..127 SysEx colour range. Raises on non-int to surface bugs."""
    if not isinstance(value, int):
        raise TypeError("colour byte must be int, got {0!r}".format(value))
    if value < 0:
        return 0
    if value > LED_COLOUR_BYTE_MAX:
        return LED_COLOUR_BYTE_MAX
    return value


def build_rgb_led_batch_sysex(led_index_to_rgb_triplet):
    """Build one or more command-03 batch-RGB SysEx messages.

    `led_index_to_rgb_triplet` is an iterable of (led_index, (r, g, b)) pairs, where
    led_index is a programmer-mode note/CC number and (r, g, b) are 0..127 ints.

    Returns a list of complete SysEx messages (each a tuple of bytes). The list has more
    than one message only when more than LPX_MAX_LED_SPECS_PER_MESSAGE LEDs are requested;
    callers send each message in turn. Returning a list (never silently truncating) keeps
    the "no quiet fallback" rule: every requested LED is represented.
    """
    led_specs = list(led_index_to_rgb_triplet)
    messages = []
    for chunk_start in range(0, len(led_specs), LPX_MAX_LED_SPECS_PER_MESSAGE):
        chunk = led_specs[chunk_start:chunk_start + LPX_MAX_LED_SPECS_PER_MESSAGE]
        message_body = []
        for led_index, rgb_triplet in chunk:
            red_byte, green_byte, blue_byte = rgb_triplet
            message_body.extend((
                LPX_LED_SPEC_TYPE_RGB,
                led_index,
                _clamp_colour_byte(red_byte),
                _clamp_colour_byte(green_byte),
                _clamp_colour_byte(blue_byte),
            ))
        messages.append(
            LPX_SYSEX_HEADER + (LPX_LED_BATCH_COMMAND_BYTE,) + tuple(message_body) + (LPX_SYSEX_END,)
        )
    return messages


# ----------------------------------------------------------------------------------------
# Colour palette. Each constant is an (r, g, b) triplet, 0..127.
# "Family" = a hue used by exactly one function, so modes are unambiguous at a glance.
# ----------------------------------------------------------------------------------------

# Universal off / empty pad.
COLOUR_OFF = (0, 0, 0)

# --- Step-state family: WHITE/AMBER hues, brightness by tuning ---------------------------
# An empty step in the sequencer area (so the 32-step grid is always visibly delimited).
COLOUR_STEP_EMPTY = (6, 6, 6)
# A filled step, coloured by its tuning index (0..3). Four clearly distinct warm hues so the
# "step colour = tuning" feature reads at a glance. This is the steps-by-tuning family.
COLOUR_STEP_BY_TUNING = (
    (0, 90, 30),    # tuning 0 -> green
    (90, 80, 0),    # tuning 1 -> yellow
    (110, 40, 0),   # tuning 2 -> orange
    (110, 0, 20),   # tuning 3 -> red
)
# The playhead cell, drawn brightest so it stands out over any step colour.
COLOUR_PLAYHEAD = (127, 127, 127)
# A filled step that currently sits under the playhead (blend: bright but tinted).
COLOUR_STEP_UNDER_PLAYHEAD = (127, 110, 90)

# --- Instrument-select family: CYAN/BLUE ------------------------------------------------
COLOUR_INSTRUMENT_AVAILABLE = (0, 30, 40)     # an instrument pad that exists but isn't selected
COLOUR_INSTRUMENT_SELECTED = (0, 90, 120)     # the currently selected instrument
COLOUR_INSTRUMENT_UNUSED = (0, 0, 0)          # spare instrument pads (idx 11..15) when idle
COLOUR_INSTRUMENT_PREVIEW_FLASH = (0, 127, 127)  # brief tap feedback when previewing

# --- Pattern-select family: VIOLET/MAGENTA ----------------------------------------------
COLOUR_PATTERN_EMPTY_SLOT = (20, 0, 25)       # a clip slot with no clip yet
COLOUR_PATTERN_HAS_CLIP = (50, 0, 70)         # a slot that holds a pattern
COLOUR_PATTERN_SELECTED = (110, 0, 127)       # the currently edited pattern slot

# --- Velocity family (right column): PINK/RED ramp, quiet(bottom)->loud(top) ------------
# Eight ascending-brightness pink levels. Distinct from the warm step family and the
# violet pattern family so the right column never reads as anything else.
COLOUR_VELOCITY_LEVELS_LOW_TO_HIGH = (
    (16, 0, 8),
    (32, 0, 12),
    (48, 0, 16),
    (64, 0, 20),
    (80, 0, 24),
    (96, 0, 28),
    (112, 0, 32),
    (127, 0, 36),
)
COLOUR_VELOCITY_SELECTED = (127, 60, 90)      # the currently chosen velocity level pad

# Idle (no step held) right-column ramp: the SAME pink hue but dimmed, so the resting column
# is clearly distinct from the bright "velocity-selector active" state shown while a step is
# held (modal-feedback principle: the hold visibly recolours the column).
COLOUR_VELOCITY_IDLE_RAMP_LEVELS_LOW_TO_HIGH = tuple(
    (red // 4, green // 4, blue // 4)
    for (red, green, blue) in COLOUR_VELOCITY_LEVELS_LOW_TO_HIGH
)
COLOUR_VELOCITY_IDLE_DEFAULT_MARK = (40, 18, 28)  # idle mark for the default-velocity level

# --- Length family (hold-Length over the step area): GREEN ------------------------------
# Used only while Length is held; distinct green so it cannot be confused with the warm
# step family it temporarily overlays.
COLOUR_LENGTH_WITHIN_LOOP = (0, 80, 0)        # steps inside the current loop length
COLOUR_LENGTH_OUTSIDE_LOOP = (0, 14, 0)       # steps beyond the loop end
COLOUR_LENGTH_LOOP_END = (0, 127, 0)          # the pad marking the current last step

# --- Resolution family (hold-Resolution over the step area): TEAL ------------------------
# The six resolution options, drawn on the first six step-area pads while Resolution is held.
# Teal is its own family, never used elsewhere, so this overlay mode is unmistakable.
COLOUR_RESOLUTION_OPTION = (0, 50, 50)         # an available resolution option pad
COLOUR_RESOLUTION_OPTION_SELECTED = (0, 127, 110)  # the currently active resolution

# --- Top-row button family: per-function tints (each button its own meaning) -------------
COLOUR_TOPBUTTON_IDLE = (10, 10, 10)          # a top-row button at rest
COLOUR_TOPBUTTON_ACTIVE = (127, 127, 0)       # a top-row button while held / engaged

# --- Tuning picker family (hold-step over the 4 option pads): reuses the step-by-tuning
#     hues so the picker literally shows the four step colours, with the active one bright.
COLOUR_TUNING_OPTION_BY_INDEX = COLOUR_STEP_BY_TUNING
COLOUR_TUNING_OPTION_SELECTED = (127, 127, 127)


def velocity_colour_for_level(level_index_low_to_high):
    """Right-column colour for velocity level 0..7 (0 = quietest / bottom)."""
    if not (0 <= level_index_low_to_high < len(COLOUR_VELOCITY_LEVELS_LOW_TO_HIGH)):
        raise ValueError("velocity level {0} out of 0..7".format(level_index_low_to_high))
    return COLOUR_VELOCITY_LEVELS_LOW_TO_HIGH[level_index_low_to_high]


def step_colour_for_tuning(tuning_index):
    """Sequencer-step colour for a filled step at the given tuning index 0..3."""
    if not (0 <= tuning_index < len(COLOUR_STEP_BY_TUNING)):
        raise ValueError("tuning index {0} out of 0..3".format(tuning_index))
    return COLOUR_STEP_BY_TUNING[tuning_index]


class LedPainter(object):
    """Builds and sends batch-RGB SysEx to repaint the Launchpad X regions.

    Pure Python: it depends only on the SysEx builder above, the palette, and lpx_layout. It
    sends MIDI through an injected callback (`send_sysex_message`) so it needs no Live import;
    the surface passes its own `_send_midi`. A full-surface redraw is cheap (<= 64 LEDs), so
    each paint_* method repaints its whole region in one (or, for safety, a few) message(s).
    """

    def __init__(self, send_sysex_message):
        # send_sysex_message(message_tuple) -> sends one complete SysEx message to the LPX.
        self._send_sysex_message = send_sysex_message

    def _send_leds(self, led_index_to_rgb_triplet):
        for message in build_rgb_led_batch_sysex(led_index_to_rgb_triplet):
            self._send_sysex_message(message)

    # ---- step sequencer area (rows 8..5) ------------------------------------------------

    def paint_step_area(
        self,
        step_index_to_cached_note,
        tuning_per_step,
        playhead_step_index,
        loop_length_in_steps,
        held_step_index,
    ):
        leds = []
        for step_index, grid_note in enumerate(lpx_layout.STEP_INDEX_TO_GRID_NOTE):
            colour = self._step_colour(
                step_index,
                step_index_to_cached_note,
                tuning_per_step,
                playhead_step_index,
                loop_length_in_steps,
                held_step_index,
            )
            leds.append((grid_note, colour))
        self._send_leds(leds)

    def _step_colour(
        self,
        step_index,
        step_index_to_cached_note,
        tuning_per_step,
        playhead_step_index,
        loop_length_in_steps,
        held_step_index,
    ):
        is_under_playhead = step_index == playhead_step_index
        has_note = step_index in step_index_to_cached_note
        if has_note:
            if is_under_playhead:
                return COLOUR_STEP_UNDER_PLAYHEAD
            tuning_index = tuning_per_step[step_index]
            return step_colour_for_tuning(tuning_index)
        # Empty step.
        if is_under_playhead:
            return COLOUR_PLAYHEAD
        if step_index >= loop_length_in_steps:
            return COLOUR_OFF  # beyond the loop end: dark, so the loop length is visible
        return COLOUR_STEP_EMPTY

    # ---- step area overlays while a top-row button is held ------------------------------

    def paint_length_overlay(self, loop_length_in_steps):
        """Hold-Length feedback: green ramp over the step area, brightest at the loop end."""
        leds = []
        loop_end_step_index = loop_length_in_steps - 1
        for step_index, grid_note in enumerate(lpx_layout.STEP_INDEX_TO_GRID_NOTE):
            if step_index == loop_end_step_index:
                colour = COLOUR_LENGTH_LOOP_END
            elif step_index < loop_length_in_steps:
                colour = COLOUR_LENGTH_WITHIN_LOOP
            else:
                colour = COLOUR_LENGTH_OUTSIDE_LOOP
            leds.append((grid_note, colour))
        self._send_leds(leds)

    def paint_resolution_overlay(self, resolution_option_count, selected_resolution_index):
        """Hold-Resolution feedback: teal option pads on the first N step-area pads."""
        leds = []
        for step_index, grid_note in enumerate(lpx_layout.STEP_INDEX_TO_GRID_NOTE):
            if step_index < resolution_option_count:
                if step_index == selected_resolution_index:
                    colour = COLOUR_RESOLUTION_OPTION_SELECTED
                else:
                    colour = COLOUR_RESOLUTION_OPTION
            else:
                colour = COLOUR_OFF
            leds.append((grid_note, colour))
        self._send_leds(leds)

    # ---- instrument-select area (bottom-left quad) --------------------------------------

    def paint_instrument_area(self, selected_instrument_index):
        leds = []
        for instrument_index, grid_note in enumerate(lpx_layout.INSTRUMENT_INDEX_TO_GRID_NOTE):
            if instrument_index >= alphabase_map.ALPHABASE_INSTRUMENT_COUNT:
                colour = COLOUR_INSTRUMENT_UNUSED
            elif instrument_index == selected_instrument_index:
                colour = COLOUR_INSTRUMENT_SELECTED
            else:
                colour = COLOUR_INSTRUMENT_AVAILABLE
            leds.append((grid_note, colour))
        self._send_leds(leds)

    def flash_instrument_preview(self, instrument_index):
        grid_note = lpx_layout.INSTRUMENT_INDEX_TO_GRID_NOTE[instrument_index]
        self._send_leds([(grid_note, COLOUR_INSTRUMENT_PREVIEW_FLASH)])

    # ---- pattern-select area (bottom-right quad) ----------------------------------------

    def paint_pattern_area(self, selected_pattern_slot_index, slot_has_clip_flags):
        leds = []
        for slot_index, grid_note in enumerate(lpx_layout.PATTERN_SLOT_INDEX_TO_GRID_NOTE):
            has_clip = slot_index < len(slot_has_clip_flags) and slot_has_clip_flags[slot_index]
            if slot_index == selected_pattern_slot_index:
                colour = COLOUR_PATTERN_SELECTED
            elif has_clip:
                colour = COLOUR_PATTERN_HAS_CLIP
            else:
                colour = COLOUR_PATTERN_EMPTY_SLOT
            leds.append((grid_note, colour))
        self._send_leds(leds)

    # ---- option pads (4 leftmost bottom-row) as the hold-step tuning picker -------------

    def paint_tuning_picker(self, selected_tuning_index):
        leds = []
        for tuning_index, grid_note in enumerate(lpx_layout.OPTION_PAD_GRID_NOTES_LEFT_TO_RIGHT):
            if tuning_index == selected_tuning_index:
                colour = COLOUR_TUNING_OPTION_SELECTED
            else:
                colour = COLOUR_TUNING_OPTION_BY_INDEX[tuning_index]
            leds.append((grid_note, colour))
        self._send_leds(leds)

    # ---- right column as the velocity selector ------------------------------------------

    def paint_velocity_column_idle(self, selected_velocity_level_index):
        """Idle right-column paint: the dim quiet->loud ramp, with the level that will be used
        for NEW steps marked. This is the always-on resting state when no step is held."""
        leds = []
        for level_index, cc_number in enumerate(
            lpx_layout.RIGHT_COLUMN_CC_NUMBERS_BOTTOM_TO_TOP
        ):
            if level_index == selected_velocity_level_index:
                colour = COLOUR_VELOCITY_IDLE_DEFAULT_MARK
            else:
                colour = COLOUR_VELOCITY_IDLE_RAMP_LEVELS_LOW_TO_HIGH[level_index]
            leds.append((cc_number, colour))
        self._send_leds(leds)

    def paint_velocity_column_active(self, selected_velocity_level_index):
        """Hold-step feedback: the right column has BECOME the velocity selector for the held
        step. Drawn with the bright ramp + bright selected pad so it is unmistakably distinct
        from the dim idle state (modal-feedback principle), highlighting the held step's level.
        Mirrors paint_tuning_picker's active rendering for symmetry."""
        leds = []
        for level_index, cc_number in enumerate(
            lpx_layout.RIGHT_COLUMN_CC_NUMBERS_BOTTOM_TO_TOP
        ):
            if level_index == selected_velocity_level_index:
                colour = COLOUR_VELOCITY_SELECTED
            else:
                colour = velocity_colour_for_level(level_index)
            leds.append((cc_number, colour))
        self._send_leds(leds)

    # ---- top-row buttons ----------------------------------------------------------------

    def paint_top_button(self, top_button_cc_number, is_active):
        colour = COLOUR_TOPBUTTON_ACTIVE if is_active else COLOUR_TOPBUTTON_IDLE
        self._send_leds([(top_button_cc_number, colour)])


def _self_check():
    # A single LED produces one well-formed message: header, cmd 03, type 3, index, rgb, end.
    messages = build_rgb_led_batch_sysex([(81, (127, 0, 0))])
    assert len(messages) == 1
    only_message = messages[0]
    assert only_message[:6] == LPX_SYSEX_HEADER
    assert only_message[6] == LPX_LED_BATCH_COMMAND_BYTE
    assert only_message[7] == LPX_LED_SPEC_TYPE_RGB
    assert only_message[8] == 81
    assert only_message[9:12] == (127, 0, 0)
    assert only_message[-1] == LPX_SYSEX_END

    # Colour bytes are clamped, never overflow 0..127.
    clamped = build_rgb_led_batch_sysex([(11, (999, -5, 200))])[0]
    assert clamped[9:12] == (127, 0, 127), clamped[9:12]

    # More than 81 LEDs splits into multiple messages, none over the limit, all LEDs kept.
    many = [(11 + i, (1, 2, 3)) for i in range(90)]
    split = build_rgb_led_batch_sysex(many)
    assert len(split) == 2, len(split)
    first_led_count = (len(split[0]) - len(LPX_SYSEX_HEADER) - 2) // 5  # -2 for cmd byte + end
    assert first_led_count == LPX_MAX_LED_SPECS_PER_MESSAGE, first_led_count
    total_leds = sum((len(m) - len(LPX_SYSEX_HEADER) - 2) // 5 for m in split)
    assert total_leds == 90, total_leds

    # Empty input -> no messages (nothing to send), never a malformed empty SysEx.
    assert build_rgb_led_batch_sysex([]) == []

    # Modal-feedback non-overlap: the families that can share a pad must be distinct colours.
    # The leftmost bottom-row option pads can be: instrument-unused, tuning options, or
    # resolution options. The step area can be: steps, length overlay, or resolution overlay.
    # Verify the FAMILY representatives are pairwise distinct.
    family_representatives = {
        "step_tuning0": COLOUR_STEP_BY_TUNING[0],
        "instrument_selected": COLOUR_INSTRUMENT_SELECTED,
        "pattern_selected": COLOUR_PATTERN_SELECTED,
        "velocity_top": COLOUR_VELOCITY_LEVELS_LOW_TO_HIGH[-1],
        "length": COLOUR_LENGTH_LOOP_END,
        "resolution": COLOUR_RESOLUTION_OPTION_SELECTED,
    }
    representative_values = list(family_representatives.values())
    assert len(set(representative_values)) == len(representative_values), family_representatives

    # Length (green) vs Resolution (teal) overlay the SAME step pads, so they must differ.
    assert COLOUR_LENGTH_LOOP_END != COLOUR_RESOLUTION_OPTION_SELECTED
    assert COLOUR_LENGTH_WITHIN_LOOP != COLOUR_RESOLUTION_OPTION

    print("lpx_led self-check passed: SysEx framing, clamping, chunking, palette non-overlap OK.")


if __name__ == "__main__":
    _self_check()
