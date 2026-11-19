# -*- coding: utf-8 -*-
"""Drum page, bottom-right 4x4: the first 16 clip slots of the target track = 16 patterns.

A press selects the slot; drum_page then binds the sequencer to its clip (and creates the
clip on the first step drawn into an empty slot). drum_page intercepts presses first
(no map / super + pad = duplicate the current pattern into that slot).
Super held: every pad except the selected one is white (a paste target).
"""

from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.base import listens, listens_group, liveobj_valid
from ableton.v2.control_surface import Component

from . import layout
from . import palette


class PatternSelectComponent(Component):

    def __init__(self, led_painter=None, is_super_held=None, *a, **k):
        super(PatternSelectComponent, self).__init__(*a, **k)
        if led_painter is None or is_super_held is None:
            raise ValueError("PatternSelectComponent needs led_painter and is_super_held")
        self._led_painter = led_painter
        self._is_super_held = is_super_held
        self._selected_pattern_slot_index = 0
        self._track = None
        self._on_pattern_selected = None
        self._pattern_press_interceptor = None

    def set_callbacks(self, on_pattern_selected, pattern_press_interceptor):
        """on_pattern_selected(slot_index); pattern_press_interceptor(slot_index) -> True if consumed."""
        self._on_pattern_selected = on_pattern_selected
        self._pattern_press_interceptor = pattern_press_interceptor

    def set_pattern_matrix(self, pattern_matrix):
        self._on_pattern_matrix_value.subject = pattern_matrix

    def set_track(self, track):
        self._track = track if liveobj_valid(track) else None
        self._on_has_clip_changed.replace_subjects(self.clip_slots_in_pattern_range())
        self.repaint()

    @property
    def selected_pattern_slot_index(self):
        return self._selected_pattern_slot_index

    def clip_slots_in_pattern_range(self):
        if self._track is None:
            return []
        return list(self._track.clip_slots)[:layout.PATTERN_SELECT_PAD_COUNT]

    @listens("value")
    def _on_pattern_matrix_value(self, value, column_index, row_index, _is_momentary):
        if value <= 0:
            return
        pattern_slot_index = row_index * layout.PATTERN_SELECT_COLUMN_COUNT + column_index
        if self._pattern_press_interceptor(pattern_slot_index):
            return
        self._selected_pattern_slot_index = pattern_slot_index
        self._on_pattern_selected(pattern_slot_index)
        self.repaint()

    @listens_group("has_clip")
    def _on_has_clip_changed(self, changed_clip_slot):
        clip_slots = self.clip_slots_in_pattern_range()
        if (self._selected_pattern_slot_index < len(clip_slots)
                and clip_slots[self._selected_pattern_slot_index] == changed_clip_slot):
            # The selected pattern gained or lost its clip (in Live or by us): rebind.
            self._on_pattern_selected(self._selected_pattern_slot_index)
        self.repaint()

    def _pad_colour(self, slot_index, clip_slots, super_held):
        if slot_index >= len(clip_slots):
            return palette.OFF  # the set has fewer scenes than pattern pads
        if slot_index == self._selected_pattern_slot_index:
            return palette.DRUM_PATTERN_SELECTED
        if super_held:
            return palette.DRUM_SUPER_PATTERN_PASTE_TARGET
        if clip_slots[slot_index].has_clip:
            return palette.DRUM_PATTERN_HAS_CLIP
        return palette.DRUM_PATTERN_EMPTY

    def repaint(self):
        if not self.is_enabled():
            return  # a disabled page never paints; drum_page.repaint_page() runs on entry
        super_held = self._is_super_held()
        clip_slots = self.clip_slots_in_pattern_range()
        self._led_painter.paint([
            (grid_note, self._pad_colour(slot_index, clip_slots, super_held))
            for slot_index, grid_note in enumerate(layout.PATTERN_SLOT_INDEX_TO_GRID_NOTE)
        ])
