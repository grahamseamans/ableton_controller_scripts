# -*- coding: utf-8 -*-
"""Launchpad X programmer-mode layout constants and region<->pad maps.

PURE PYTHON. No Live / ableton imports, so it is unit-testable with `uv run python lpx_layout.py`.

Programmer mode facts (knowledge_base/hardware/novation_launchpad_x/notes.md, Programmer's
Reference p.10-15), all on MIDI channel 1:

  - 8x8 grid pad -> Note On, note = row*10 + col, bottom-left = 11, top-right = 88.
  - Top round row (8) -> CC 91..98 (left -> right).
  - Right round column (8) -> CC 19,29,39,49,59,69,79,89 (bottom -> top).
  - Logo -> CC 99.
  - Enter programmer mode: F0 00 20 29 02 0C 0E 01 F7 ; revert to Live mode: ...0E 00 F7.

Region layout (ARCHITECTURE/architecture.md + midi_mappings.md section B):

  rows 8..5  -> 32-step sequencer; step 1 = note 81 (top-left), order left->right then down.
  rows 4..1, cols 1..4 -> instrument select (idx 0..15, 0..10 used).
  rows 4..1, cols 5..8 -> pattern select (clip slot 0..15).
  The 4 leftmost bottom-row pads (notes 11..14) double as the hold-step tuning picker and
  the hold-Resolution option pads (see the modal-feedback gesture in architecture.md).
"""

from __future__ import absolute_import, print_function, unicode_literals

# ----------------------------------------------------------------------------------------
# Grid geometry
# ----------------------------------------------------------------------------------------

GRID_SIDE_LENGTH_IN_PADS = 8  # the LPX is an 8x8 pad grid

# Programmer-mode grid pads are addressed as note = row*10 + col, row/col both 1..8.
# Row 1 is the BOTTOM row, row 8 is the TOP row.
GRID_ROW_NUMBERS_TOP_TO_BOTTOM = (8, 7, 6, 5, 4, 3, 2, 1)
GRID_COLUMN_NUMBERS_LEFT_TO_RIGHT = (1, 2, 3, 4, 5, 6, 7, 8)


def grid_note_for_row_and_column(row_number_one_based, column_number_one_based):
    """note = row*10 + col for the 8x8 grid in programmer mode (row 1 bottom, row 8 top)."""
    if not (1 <= row_number_one_based <= GRID_SIDE_LENGTH_IN_PADS):
        raise ValueError("row {0} out of 1..8".format(row_number_one_based))
    if not (1 <= column_number_one_based <= GRID_SIDE_LENGTH_IN_PADS):
        raise ValueError("column {0} out of 1..8".format(column_number_one_based))
    return row_number_one_based * 10 + column_number_one_based


# ----------------------------------------------------------------------------------------
# Round buttons (CC, channel 1)
# ----------------------------------------------------------------------------------------

# Top round row, left -> right.
TOP_ROW_CC_NUMBERS_LEFT_TO_RIGHT = (91, 92, 93, 94, 95, 96, 97, 98)

# Right round column, BOTTOM -> TOP (so index 0 is the lowest pad).
RIGHT_COLUMN_CC_NUMBERS_BOTTOM_TO_TOP = (19, 29, 39, 49, 59, 69, 79, 89)

# The logo LED.
LOGO_CC_NUMBER = 99

# Semantic names for the 8 top-row buttons, matching architecture.md "Buttons" table,
# in left->right order so the index lines up with TOP_ROW_CC_NUMBERS_LEFT_TO_RIGHT.
TOP_ROW_BUTTON_COPY = "copy"
TOP_ROW_BUTTON_PASTE = "paste"
TOP_ROW_BUTTON_LENGTH = "length"
TOP_ROW_BUTTON_RESOLUTION = "resolution"
TOP_ROW_BUTTON_PREVIEW = "preview"
TOP_ROW_BUTTON_SOLO = "solo"
TOP_ROW_BUTTON_NUDGE_LEFT = "nudge_left"
TOP_ROW_BUTTON_NUDGE_RIGHT = "nudge_right"

TOP_ROW_BUTTON_NAMES_LEFT_TO_RIGHT = (
    TOP_ROW_BUTTON_COPY,
    TOP_ROW_BUTTON_PASTE,
    TOP_ROW_BUTTON_LENGTH,
    TOP_ROW_BUTTON_RESOLUTION,
    TOP_ROW_BUTTON_PREVIEW,
    TOP_ROW_BUTTON_SOLO,
    TOP_ROW_BUTTON_NUDGE_LEFT,
    TOP_ROW_BUTTON_NUDGE_RIGHT,
)

# CC number for each named top-row button.
TOP_ROW_CC_FOR_BUTTON_NAME = dict(
    zip(TOP_ROW_BUTTON_NAMES_LEFT_TO_RIGHT, TOP_ROW_CC_NUMBERS_LEFT_TO_RIGHT)
)

# ----------------------------------------------------------------------------------------
# Enter / exit programmer-mode SysEx
# ----------------------------------------------------------------------------------------

# Common header for all Launchpad X SysEx (F0 00 20 29 02 0C).
LPX_SYSEX_HEADER = (0xF0, 0x00, 0x20, 0x29, 0x02, 0x0C)
LPX_SYSEX_END = 0xF7

# SysEx command 0x0E selects the LPX layout/firmware mode; its value byte chooses the mode.
LPX_LAYOUT_MODE_COMMAND_BYTE = 0x0E
LPX_PROGRAMMER_MODE_VALUE_BYTE = 0x01  # value -> enter Programmer mode (custom script control)
LPX_LIVE_MODE_VALUE_BYTE = 0x00        # value -> revert to Live/standalone mode

ENTER_PROGRAMMER_MODE_SYSEX = (
    LPX_SYSEX_HEADER + (LPX_LAYOUT_MODE_COMMAND_BYTE, LPX_PROGRAMMER_MODE_VALUE_BYTE, LPX_SYSEX_END)
)
ENTER_LIVE_MODE_SYSEX = (
    LPX_SYSEX_HEADER + (LPX_LAYOUT_MODE_COMMAND_BYTE, LPX_LIVE_MODE_VALUE_BYTE, LPX_SYSEX_END)
)

# Identity (Universal Device Inquiry response) bytes the framework matches to confirm an LPX is
# attached before calling on_identified. Manufacturer (0,32,41) + LP X family (3,1) + member
# (0,0), per the decompiled novation/sysex.py + Launchpad_X/sysex_ids.py.
LPX_PRODUCT_ID_BYTES = (0x00, 0x20, 0x29, 0x03, 0x01, 0x00, 0x00)

# ----------------------------------------------------------------------------------------
# Step-sequencer region: rows 8..5, 32 pads, step 1 = top-left (note 81)
# ----------------------------------------------------------------------------------------

STEP_SEQUENCER_ROW_NUMBERS_TOP_TO_BOTTOM = (8, 7, 6, 5)
STEP_COUNT = len(STEP_SEQUENCER_ROW_NUMBERS_TOP_TO_BOTTOM) * GRID_SIDE_LENGTH_IN_PADS  # 32


def _build_step_index_to_grid_note():
    """step_index 0..31 -> grid note, order left->right within a row then top->down."""
    step_index_to_note = []
    for row_number in STEP_SEQUENCER_ROW_NUMBERS_TOP_TO_BOTTOM:
        for column_number in GRID_COLUMN_NUMBERS_LEFT_TO_RIGHT:
            step_index_to_note.append(grid_note_for_row_and_column(row_number, column_number))
    return tuple(step_index_to_note)


STEP_INDEX_TO_GRID_NOTE = _build_step_index_to_grid_note()
GRID_NOTE_TO_STEP_INDEX = {note: index for index, note in enumerate(STEP_INDEX_TO_GRID_NOTE)}

# ----------------------------------------------------------------------------------------
# Instrument-select region: rows 4..1, cols 1..4 (idx 0..15, row-major top->down)
# ----------------------------------------------------------------------------------------

INSTRUMENT_SELECT_ROW_NUMBERS_TOP_TO_BOTTOM = (4, 3, 2, 1)
INSTRUMENT_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT = (1, 2, 3, 4)
INSTRUMENT_SELECT_PAD_COUNT = (
    len(INSTRUMENT_SELECT_ROW_NUMBERS_TOP_TO_BOTTOM)
    * len(INSTRUMENT_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT)
)  # 16


def _build_instrument_index_to_grid_note():
    instrument_index_to_note = []
    for row_number in INSTRUMENT_SELECT_ROW_NUMBERS_TOP_TO_BOTTOM:
        for column_number in INSTRUMENT_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT:
            instrument_index_to_note.append(
                grid_note_for_row_and_column(row_number, column_number)
            )
    return tuple(instrument_index_to_note)


INSTRUMENT_INDEX_TO_GRID_NOTE = _build_instrument_index_to_grid_note()
GRID_NOTE_TO_INSTRUMENT_INDEX = {
    note: index for index, note in enumerate(INSTRUMENT_INDEX_TO_GRID_NOTE)
}

# ----------------------------------------------------------------------------------------
# Pattern-select region: rows 4..1, cols 5..8 (clip slot 0..15, same scheme)
# ----------------------------------------------------------------------------------------

PATTERN_SELECT_ROW_NUMBERS_TOP_TO_BOTTOM = (4, 3, 2, 1)
PATTERN_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT = (5, 6, 7, 8)
PATTERN_SELECT_PAD_COUNT = (
    len(PATTERN_SELECT_ROW_NUMBERS_TOP_TO_BOTTOM)
    * len(PATTERN_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT)
)  # 16


def _build_pattern_slot_index_to_grid_note():
    pattern_slot_index_to_note = []
    for row_number in PATTERN_SELECT_ROW_NUMBERS_TOP_TO_BOTTOM:
        for column_number in PATTERN_SELECT_COLUMN_NUMBERS_LEFT_TO_RIGHT:
            pattern_slot_index_to_note.append(
                grid_note_for_row_and_column(row_number, column_number)
            )
    return tuple(pattern_slot_index_to_note)


PATTERN_SLOT_INDEX_TO_GRID_NOTE = _build_pattern_slot_index_to_grid_note()
GRID_NOTE_TO_PATTERN_SLOT_INDEX = {
    note: index for index, note in enumerate(PATTERN_SLOT_INDEX_TO_GRID_NOTE)
}

# ----------------------------------------------------------------------------------------
# Option pads: the 4 leftmost bottom-row pads (notes 11..14).
# Normally spare instrument pads (instrument idx 12..15, unused); under a hold gesture they
# become the tuning picker (hold-step) or resolution options (hold-Resolution).
# ----------------------------------------------------------------------------------------

OPTION_PAD_GRID_NOTES_LEFT_TO_RIGHT = tuple(
    grid_note_for_row_and_column(1, column_number) for column_number in (1, 2, 3, 4)
)  # (11, 12, 13, 14)


def _self_check():
    # Grid note formula.
    assert grid_note_for_row_and_column(1, 1) == 11
    assert grid_note_for_row_and_column(8, 8) == 88

    # Step region: 32 steps, step 0 == 81 (top-left), order left->right then down.
    assert STEP_COUNT == 32, STEP_COUNT
    assert STEP_INDEX_TO_GRID_NOTE[0] == 81, STEP_INDEX_TO_GRID_NOTE[0]
    assert STEP_INDEX_TO_GRID_NOTE[7] == 88  # end of top row
    assert STEP_INDEX_TO_GRID_NOTE[8] == 71  # start of next row down
    assert STEP_INDEX_TO_GRID_NOTE[31] == 58  # last step, bottom-right of the step area
    assert GRID_NOTE_TO_STEP_INDEX[81] == 0
    assert set(STEP_INDEX_TO_GRID_NOTE) == {
        81, 82, 83, 84, 85, 86, 87, 88,
        71, 72, 73, 74, 75, 76, 77, 78,
        61, 62, 63, 64, 65, 66, 67, 68,
        51, 52, 53, 54, 55, 56, 57, 58,
    }

    # Instrument select: idx 0 == 41, idx 15 == 14 (row-major top->down, cols 1..4).
    assert INSTRUMENT_SELECT_PAD_COUNT == 16
    assert INSTRUMENT_INDEX_TO_GRID_NOTE[0] == 41
    assert INSTRUMENT_INDEX_TO_GRID_NOTE[3] == 44
    assert INSTRUMENT_INDEX_TO_GRID_NOTE[4] == 31
    assert INSTRUMENT_INDEX_TO_GRID_NOTE[15] == 14
    assert GRID_NOTE_TO_INSTRUMENT_INDEX[11] == 12  # leftmost bottom-row pad is idx 12

    # Pattern select: slot 0 == 45, slot 15 == 18 (cols 5..8).
    assert PATTERN_SELECT_PAD_COUNT == 16
    assert PATTERN_SLOT_INDEX_TO_GRID_NOTE[0] == 45
    assert PATTERN_SLOT_INDEX_TO_GRID_NOTE[15] == 18

    # Step area, instrument area and pattern area are mutually exclusive sets of pads.
    step_notes = set(STEP_INDEX_TO_GRID_NOTE)
    instrument_notes = set(INSTRUMENT_INDEX_TO_GRID_NOTE)
    pattern_notes = set(PATTERN_SLOT_INDEX_TO_GRID_NOTE)
    assert step_notes.isdisjoint(instrument_notes)
    assert step_notes.isdisjoint(pattern_notes)
    assert instrument_notes.isdisjoint(pattern_notes)
    # Together they tile all 64 grid pads.
    assert len(step_notes | instrument_notes | pattern_notes) == 64

    # Option pads are the 4 leftmost bottom-row pads, which are the spare instrument pads.
    assert OPTION_PAD_GRID_NOTES_LEFT_TO_RIGHT == (11, 12, 13, 14)
    for option_note in OPTION_PAD_GRID_NOTES_LEFT_TO_RIGHT:
        assert option_note in instrument_notes

    # Round-button maps.
    assert TOP_ROW_CC_FOR_BUTTON_NAME[TOP_ROW_BUTTON_RESOLUTION] == 94
    assert len(TOP_ROW_BUTTON_NAMES_LEFT_TO_RIGHT) == 8
    assert RIGHT_COLUMN_CC_NUMBERS_BOTTOM_TO_TOP[0] == 19
    assert RIGHT_COLUMN_CC_NUMBERS_BOTTOM_TO_TOP[7] == 89

    # SysEx.
    assert ENTER_PROGRAMMER_MODE_SYSEX == (0xF0, 0x00, 0x20, 0x29, 0x02, 0x0C, 0x0E, 0x01, 0xF7)
    assert ENTER_LIVE_MODE_SYSEX == (0xF0, 0x00, 0x20, 0x29, 0x02, 0x0C, 0x0E, 0x00, 0xF7)

    print("lpx_layout self-check passed: regions tile the grid, step1=81, programmer SysEx OK.")


if __name__ == "__main__":
    _self_check()
