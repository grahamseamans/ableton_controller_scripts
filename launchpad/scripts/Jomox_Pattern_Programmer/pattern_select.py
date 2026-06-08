# -*- coding: utf-8 -*-
"""Bottom-right 4x4 quad: select which clip slot (pattern) on the AlphaBase track to edit.

16 pads = the first 16 clip slots of the single AlphaBase track = 16 patterns. Tapping a pad
binds the sequencer to that slot's clip; if the slot is empty it stays empty until the user
draws a step, at which point the surface creates the clip (the surface owns clip creation so
this component never fabricates data on its own).

Imports Live/ableton -> only runs inside Ableton. Follows the decompiled v2 idioms.
"""

from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.base import listens, listens_group, liveobj_valid
from ableton.v2.control_surface import Component

from . import lpx_layout


class PatternSelectComponent(Component):
    """Selects the active clip slot (pattern) and reports slot occupancy for LED feedback."""

    def __init__(self, led_painter=None, *a, **k):
        super(PatternSelectComponent, self).__init__(*a, **k)
        self._led_painter = led_painter
        self._selected_pattern_slot_index = 0
        self._pattern_matrix = None
        self._track = None

        # Injected by the surface: on_pattern_selected(slot_index) -> rebind the clip.
        self._on_pattern_selected = None

    def set_callbacks(self, on_pattern_selected):
        self._on_pattern_selected = on_pattern_selected

    def set_track(self, track):
        """The single AlphaBase track whose clip slots are the patterns."""
        self._track = track if liveobj_valid(track) else None
        self._register_clip_slot_listeners()
        self._repaint()

    # ---- element wiring -----------------------------------------------------------------

    def set_pattern_matrix(self, pattern_matrix):
        if pattern_matrix:
            pattern_matrix.reset()
        self._pattern_matrix = pattern_matrix
        self._PatternSelectComponent__on_pattern_matrix_value.subject = self._pattern_matrix
        self._repaint()

    @property
    def selected_pattern_slot_index(self):
        return self._selected_pattern_slot_index

    @listens("value")
    def __on_pattern_matrix_value(self, value, column, row, is_momentary):
        if value <= 0:
            return  # press only
        # The pattern matrix is 4 wide x 4 tall (rows 4..1, cols 5..8). Row 0 == top row.
        pattern_slot_index = row * 4 + column
        self._select_pattern_slot(pattern_slot_index)

    def _select_pattern_slot(self, pattern_slot_index):
        self._selected_pattern_slot_index = pattern_slot_index
        if self._on_pattern_selected is not None:
            self._on_pattern_selected(pattern_slot_index)
        self._repaint()

    # ---- clip-slot occupancy listeners --------------------------------------------------

    def _clip_slots_in_pattern_range(self):
        if self._track is None:
            return []
        clip_slots = self._track.clip_slots
        return list(clip_slots[:lpx_layout.PATTERN_SELECT_PAD_COUNT])

    def _register_clip_slot_listeners(self):
        # Repaint when any pattern slot gains or loses a clip, so the LEDs track occupancy.
        self._PatternSelectComponent__on_has_clip_changed.replace_subjects(
            self._clip_slots_in_pattern_range()
        )

    @listens_group("has_clip")
    def __on_has_clip_changed(self, _clip_slot):
        self._repaint()

    def _slot_has_clip_flags(self):
        flags = []
        for clip_slot in self._clip_slots_in_pattern_range():
            flags.append(bool(clip_slot.has_clip))
        return flags

    def _repaint(self):
        if self._led_painter is None:
            return
        self._led_painter.paint_pattern_area(
            selected_pattern_slot_index=self._selected_pattern_slot_index,
            slot_has_clip_flags=self._slot_has_clip_flags(),
        )

    def update(self):
        super(PatternSelectComponent, self).update()
        if self.is_enabled():
            self._repaint()
