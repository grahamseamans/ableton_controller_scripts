# -*- coding: utf-8 -*-
"""Every Launchpad X control element the script uses (Programmer mode, MIDI channel 1).

Imports Live's framework, so it only runs inside Ableton. Built inside the surface's
component_guard. No element here ever lights itself with a colour: all LEDs go through
led.LedPainter. (A ButtonElement's reset() sends value 0 when a Layer grabs it; the page's
repaint runs after that, see surface.py.)
"""

from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.control_surface import MIDI_CC_TYPE, MIDI_NOTE_TYPE
from ableton.v2.control_surface.elements import ButtonElement, ButtonMatrixElement, SysexElement

from . import layout

MIDI_CHANNEL_ZERO_BASED = 0


def _create_button(identifier, message_type, name):
    return ButtonElement(True, message_type, MIDI_CHANNEL_ZERO_BASED, identifier, name=name)


class LpxElements(object):

    def __init__(self):
        self.firmware_mode_switch = SysexElement(
            name="Firmware_Mode_Switch",
            send_message_generator=layout.firmware_mode_sysex,
        )

        # 8x8 grid, rows top -> bottom, columns left -> right.
        grid_rows_top_to_bottom = []
        for row_number in layout.GRID_ROW_NUMBERS_TOP_TO_BOTTOM:
            grid_rows_top_to_bottom.append([
                _create_button(
                    layout.grid_note_for_row_and_column(row_number, column_number),
                    MIDI_NOTE_TYPE,
                    "Grid_Pad_{0}".format(layout.grid_note_for_row_and_column(row_number, column_number)),
                )
                for column_number in layout.GRID_COLUMN_NUMBERS_LEFT_TO_RIGHT
            ])
        self.grid_matrix = ButtonMatrixElement(rows=grid_rows_top_to_bottom, name="Grid_Matrix")

        # Drum page sub-matrices of the same pads.
        step_row_count = len(layout.STEP_SEQUENCER_ROW_NUMBERS_TOP_TO_BOTTOM)
        self.step_matrix = ButtonMatrixElement(
            rows=grid_rows_top_to_bottom[:step_row_count], name="Step_Matrix"
        )
        self.voice_matrix = ButtonMatrixElement(
            rows=[row[:layout.VOICE_SELECT_COLUMN_COUNT] for row in grid_rows_top_to_bottom[step_row_count:]],
            name="Voice_Matrix",
        )
        self.pattern_matrix = ButtonMatrixElement(
            rows=[row[layout.VOICE_SELECT_COLUMN_COUNT:] for row in grid_rows_top_to_bottom[step_row_count:]],
            name="Pattern_Matrix",
        )

        # Right column as an 8-row x 1-column matrix, row 0 = TOP button.
        self.right_column_matrix = ButtonMatrixElement(
            rows=[
                [_create_button(cc_number, MIDI_CC_TYPE, "Right_Column_{0}".format(cc_number))]
                for cc_number in layout.RIGHT_COLUMN_CC_NUMBERS_TOP_TO_BOTTOM
            ],
            name="Right_Column_Matrix",
        )

        self.up_button = _create_button(layout.ARROW_UP_CC_NUMBER, MIDI_CC_TYPE, "Up_Button")
        self.down_button = _create_button(layout.ARROW_DOWN_CC_NUMBER, MIDI_CC_TYPE, "Down_Button")
        self.left_button = _create_button(layout.ARROW_LEFT_CC_NUMBER, MIDI_CC_TYPE, "Left_Button")
        self.right_button = _create_button(layout.ARROW_RIGHT_CC_NUMBER, MIDI_CC_TYPE, "Right_Button")

        # Global (never in a page Layer).
        self.session_page_button = _create_button(layout.SESSION_BUTTON_CC_NUMBER, MIDI_CC_TYPE, "Session_Page_Button")
        self.drum_page_button = _create_button(layout.NOTE_BUTTON_CC_NUMBER, MIDI_CC_TYPE, "Drum_Page_Button")
        self.snapshot_page_button = _create_button(layout.CUSTOM_BUTTON_CC_NUMBER, MIDI_CC_TYPE, "Snapshot_Page_Button")
        self.super_button = _create_button(layout.CAPTURE_MIDI_BUTTON_CC_NUMBER, MIDI_CC_TYPE, "Super_Button")
