# -*- coding: utf-8 -*-
"""Bottom-left 4x4 quad: select which AlphaBase instrument the step grid edits.

11 of the 16 pads are real instruments (idx 0..10); the remaining 5 (idx 11..15) are spare.
The 4 leftmost bottom-row pads (grid notes 11..14, which are instrument idx 12..15) double as
the hold-step tuning picker and the hold-Resolution option pads; this component only paints
them as spare/unused while no hold gesture is active, and the surface overrides them during a
hold (modal feedback).

With Preview ON (top-row Preview button), tapping an instrument pad auditions it: the script
forwards the keymap note to the armed track's input, Launchpad95-style. The actual note
forwarding is performed by the surface (it owns the MIDI output); this component just reports
the tap and asks for a preview.

Imports Live/ableton -> only runs inside Ableton. Follows the decompiled v2 idioms.
"""

from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.base import listens
from ableton.v2.control_surface import Component

from . import alphabase_map


class InstrumentSelectComponent(Component):
    """Selects the active instrument and (with Preview) auditions it."""

    def __init__(self, led_painter=None, *a, **k):
        super(InstrumentSelectComponent, self).__init__(*a, **k)
        self._led_painter = led_painter
        self._selected_instrument_index = 0
        self._instrument_matrix = None

        # Callbacks injected by the surface so this component stays decoupled from clip/MIDI.
        # on_instrument_selected(instrument_index) -> rebind the sequencer's lane.
        self._on_instrument_selected = None
        # request_preview(instrument_index) -> forward the keymap note to the armed track.
        self._request_preview = None
        # is_preview_enabled() -> bool, reads the Preview top-row toggle.
        self._is_preview_enabled = None

    def set_callbacks(self, on_instrument_selected, request_preview, is_preview_enabled):
        self._on_instrument_selected = on_instrument_selected
        self._request_preview = request_preview
        self._is_preview_enabled = is_preview_enabled

    # ---- element wiring -----------------------------------------------------------------

    def set_instrument_matrix(self, instrument_matrix):
        if instrument_matrix:
            instrument_matrix.reset()
        self._instrument_matrix = instrument_matrix
        self._InstrumentSelectComponent__on_instrument_matrix_value.subject = (
            self._instrument_matrix
        )
        self._repaint()

    @property
    def selected_instrument_index(self):
        return self._selected_instrument_index

    @listens("value")
    def __on_instrument_matrix_value(self, value, column, row, is_momentary):
        if value <= 0:
            return  # act on press only
        # The instrument matrix is 4 wide x 4 tall (rows 4..1, cols 1..4). Row 0 == top row.
        instrument_index = row * 4 + column
        if instrument_index >= alphabase_map.ALPHABASE_INSTRUMENT_COUNT:
            # A spare pad (idx 11..15). It is NOT an instrument; explicitly ignore it here.
            # (Under a hold gesture the surface, not us, owns these pads.)
            return
        self._select_instrument(instrument_index)
        if self._is_preview_enabled is not None and self._is_preview_enabled():
            if self._request_preview is not None:
                self._request_preview(instrument_index)
            if self._led_painter is not None:
                self._led_painter.flash_instrument_preview(instrument_index)

    def _select_instrument(self, instrument_index):
        if instrument_index == self._selected_instrument_index:
            return
        self._selected_instrument_index = instrument_index
        if self._on_instrument_selected is not None:
            self._on_instrument_selected(instrument_index)
        self._repaint()

    def _repaint(self):
        if self._led_painter is None:
            return
        self._led_painter.paint_instrument_area(self._selected_instrument_index)

    def update(self):
        super(InstrumentSelectComponent, self).update()
        if self.is_enabled():
            self._repaint()
