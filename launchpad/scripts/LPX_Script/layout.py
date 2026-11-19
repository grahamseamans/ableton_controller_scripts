# -*- coding: utf-8 -*-
"""Launchpad X programmer-mode layout: note/CC numbers, region index maps, SysEx bytes.

PURE PYTHON (no Live import). Self-check: `uv run python layout.py`.

Sources (Programmer mode, all on MIDI channel 1):
  - LPX Programmer's Reference pp.5, 7-8, 10, 18, 21
    (/workspace/controller-system/reference/novation-launchpad-x-programmers-reference.pdf)
  - knowledge_base/hardware/novation_launchpad_x/notes.md
  - knowledge_base/.../Live12/Launchpad_X/elements.py and novation/launchpad_elements.py
    (physical labels of the top-row buttons)

  8x8 grid pad    -> Note, note = row*10 + col, bottom-left 11, top-right 88
  Top round row   -> CC 91..98 left->right: Up, Down, Left, Right, Session, Note, Custom, Capture MIDI
  Right column    -> CC 19,29,...,89 bottom->top
  Logo            -> CC 99 (LED only)
  Enter Programmer mode F0 00 20 29 02 0C 0E 01 F7, back to Live mode ...0E 00 F7
"""

from __future__ import absolute_import, print_function, unicode_literals

# ---- grid -------------------------------------------------------------------------------

GRID_SIDE_LENGTH_IN_PADS = 8
GRID_ROW_NUMBERS_TOP_TO_BOTTOM = (8, 7, 6, 5, 4, 3, 2, 1)
GRID_COLUMN_NUMBERS_LEFT_TO_RIGHT = (1, 2, 3, 4, 5, 6, 7, 8)


def grid_note_for_row_and_column(row_number_one_based, column_number_one_based):
    """note = row*10 + col (row 1 = bottom, row 8 = top). Raises on out-of-range input."""
    if not (1 <= row_number_one_based <= GRID_SIDE_LENGTH_IN_PADS):
        raise ValueError("row {0} out of 1..8".format(row_number_one_based))
    if not (1 <= column_number_one_based <= GRID_SIDE_LENGTH_IN_PADS):
        raise ValueError("column {0} out of 1..8".format(column_number_one_based))
    return row_number_one_based * 10 + column_number_one_based


# All 64 grid notes, top row first, left->right within a row. Index = row_from_top*8 + column.
ALL_GRID_NOTES_TOP_LEFT_FIRST = tuple(
    grid_note_for_row_and_column(row_number, column_number)
    for row_number in GRID_ROW_NUMBERS_TOP_TO_BOTTOM
    for column_number in GRID_COLUMN_NUMBERS_LEFT_TO_RIGHT
)


def grid_note_for_matrix_position(column_index_from_left, row_index_from_top):
    """The grid note for a (column, row) position in the full 8x8 ButtonMatrixElement."""
    return ALL_GRID_NOTES_TOP_LEFT_FIRST[
        row_index_from_top * GRID_SIDE_LENGTH_IN_PADS + column_index_from_left
    ]


# ---- round buttons ----------------------------------------------------------------------

# Top row, by physical label (Launchpad_X/elements.py names them up/down/left/right, session,
# note, custom, capture_midi).
ARROW_UP_CC_NUMBER = 91
ARROW_DOWN_CC_NUMBER = 92
ARROW_LEFT_CC_NUMBER = 93
ARROW_RIGHT_CC_NUMBER = 94
SESSION_BUTTON_CC_NUMBER = 95
NOTE_BUTTON_CC_NUMBER = 96
CUSTOM_BUTTON_CC_NUMBER = 97
CAPTURE_MIDI_BUTTON_CC_NUMBER = 98

ARROW_CC_NUMBERS_UP_DOWN_LEFT_RIGHT = (
    ARROW_UP_CC_NUMBER,
    ARROW_DOWN_CC_NUMBER,
    ARROW_LEFT_CC_NUMBER,
    ARROW_RIGHT_CC_NUMBER,
)

# Right column, BOTTOM -> TOP (index 0 = lowest button).
RIGHT_COLUMN_CC_NUMBERS_BOTTOM_TO_TOP = (19, 29, 39, 49, 59, 69, 79, 89)
# Same buttons, TOP -> BOTTOM (index 0 = top button = scene 1 on the session page).
RIGHT_COLUMN_CC_NUMBERS_TOP_TO_BOTTOM = tuple(reversed(RIGHT_COLUMN_CC_NUMBERS_BOTTOM_TO_TOP))

LOGO_CC_NUMBER = 99

# Every LED a page owns: grid + right column + arrows. Painted black in one batch on page entry.
PAGE_OWNED_LED_INDICES = (
    ALL_GRID_NOTES_TOP_LEFT_FIRST
    + RIGHT_COLUMN_CC_NUMBERS_BOTTOM_TO_TOP
    + ARROW_CC_NUMBERS_UP_DOWN_LEFT_RIGHT
)

# ---- SysEx ------------------------------------------------------------------------------

LPX_SYSEX_HEADER = (0xF0, 0x00, 0x20, 0x29, 0x02, 0x0C)
LPX_SYSEX_END = 0xF7
LPX_LAYOUT_MODE_COMMAND_BYTE = 0x0E
LPX_PROGRAMMER_MODE_VALUE_BYTE = 0x01
LPX_LIVE_MODE_VALUE_BYTE = 0x00

# Identity-response product bytes the framework matches before on_identified
# (novation/sysex.py + Launchpad_X/sysex_ids.py).
LPX_PRODUCT_ID_BYTES = (0x00, 0x20, 0x29, 0x03, 0x01, 0x00, 0x00)


def firmware_mode_sysex(mode_value_byte):
    return LPX_SYSEX_HEADER + (LPX_LAYOUT_MODE_COMMAND_BYTE, mode_value_byte, LPX_SYSEX_END)


# ---- drum page regions ------------------------------------------------------------------

# Steps: rows 8..5, 32 pads, step 0 = note 81 (top-left), left->right then down.
STEP_SEQUENCER_ROW_NUMBERS_TOP_TO_BOTTOM = (8, 7, 6, 5)
STEP_COUNT = len(STEP_SEQUENCER_ROW_NUMBERS_TOP_TO_BOTTOM) * GRID_SIDE_LENGTH_IN_PADS


def _build_region(row_numbers_top_to_bottom, column_numbers_left_to_right):
    return tuple(
        grid_note_for_row_and_column(row_number, column_number)
        for row_number in row_numbers_top_to_bottom
        for column_number in column_numbers_left_to_right
    )


STEP_INDEX_TO_GRID_NOTE = _build_region(
    STEP_SEQUENCER_ROW_NUMBERS_TOP_TO_BOTTOM, GRID_COLUMN_NUMBERS_LEFT_TO_RIGHT
)

# Voices: rows 4..1, cols 1..4 (index 0..15 row-major, top-left first).
VOICE_SELECT_ROW_NUMBERS_TOP_TO_BOTTOM = (4, 3, 2, 1)
VOICE_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT = (1, 2, 3, 4)
VOICE_INDEX_TO_GRID_NOTE = _build_region(
    VOICE_SELECT_ROW_NUMBERS_TOP_TO_BOTTOM, VOICE_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT
)
VOICE_SELECT_PAD_COUNT = len(VOICE_INDEX_TO_GRID_NOTE)
VOICE_SELECT_COLUMN_COUNT = len(VOICE_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT)

# Patterns: rows 4..1, cols 5..8 (clip slot 0..15, same scheme).
PATTERN_SELECT_ROW_NUMBERS_TOP_TO_BOTTOM = (4, 3, 2, 1)
PATTERN_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT = (5, 6, 7, 8)
PATTERN_SLOT_INDEX_TO_GRID_NOTE = _build_region(
    PATTERN_SELECT_ROW_NUMBERS_TOP_TO_BOTTOM, PATTERN_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT
)
PATTERN_SELECT_PAD_COUNT = len(PATTERN_SLOT_INDEX_TO_GRID_NOTE)
PATTERN_SELECT_COLUMN_COUNT = len(PATTERN_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT)


def _self_check():
    assert grid_note_for_row_and_column(1, 1) == 11
    assert grid_note_for_row_and_column(8, 8) == 88
    assert len(ALL_GRID_NOTES_TOP_LEFT_FIRST) == 64
    assert grid_note_for_matrix_position(0, 0) == 81
    assert grid_note_for_matrix_position(7, 7) == 18

    assert STEP_COUNT == 32
    assert STEP_INDEX_TO_GRID_NOTE[0] == 81
    assert STEP_INDEX_TO_GRID_NOTE[8] == 71
    assert STEP_INDEX_TO_GRID_NOTE[31] == 58
    assert VOICE_INDEX_TO_GRID_NOTE[0] == 41 and VOICE_INDEX_TO_GRID_NOTE[15] == 14
    assert PATTERN_SLOT_INDEX_TO_GRID_NOTE[0] == 45 and PATTERN_SLOT_INDEX_TO_GRID_NOTE[15] == 18
    step_notes = set(STEP_INDEX_TO_GRID_NOTE)
    voice_notes = set(VOICE_INDEX_TO_GRID_NOTE)
    pattern_notes = set(PATTERN_SLOT_INDEX_TO_GRID_NOTE)
    assert step_notes.isdisjoint(voice_notes) and step_notes.isdisjoint(pattern_notes)
    assert voice_notes.isdisjoint(pattern_notes)
    assert (step_notes | voice_notes | pattern_notes) == set(ALL_GRID_NOTES_TOP_LEFT_FIRST)

    assert RIGHT_COLUMN_CC_NUMBERS_TOP_TO_BOTTOM[0] == 89
    assert len(PAGE_OWNED_LED_INDICES) == 76 and len(set(PAGE_OWNED_LED_INDICES)) == 76
    assert firmware_mode_sysex(LPX_PROGRAMMER_MODE_VALUE_BYTE) == (
        0xF0, 0x00, 0x20, 0x29, 0x02, 0x0C, 0x0E, 0x01, 0xF7)
    assert firmware_mode_sysex(LPX_LIVE_MODE_VALUE_BYTE)[-2] == 0x00
    print("layout self-check passed (^_^)b regions tile the grid, 76 page LEDs, SysEx OK.")


if __name__ == "__main__":
    _self_check()
