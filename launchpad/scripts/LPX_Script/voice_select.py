# -*- coding: utf-8 -*-
"""Drum page, bottom-left 4x4: pick the voice the step grid edits. Pads come from the DrumMap
(row-major, top-left first); pads past the map's last voice are unused and dark.

No drum map on the target track: every pad is dim red and presses do nothing (drum_page logs).
Super held: pads with a voice turn red (super + voice pad clears that voice's lane).
drum_page intercepts presses first (no map / super); otherwise a press selects the voice.
"""

from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.base import listens
from ableton.v2.control_surface import Component

from . import layout
from . import palette


class VoiceSelectComponent(Component):

    def __init__(self, led_painter=None, is_super_held=None, *a, **k):
        super(VoiceSelectComponent, self).__init__(*a, **k)
        if led_painter is None or is_super_held is None:
            raise ValueError("VoiceSelectComponent needs led_painter and is_super_held")
        self._led_painter = led_painter
        self._is_super_held = is_super_held
        self._drum_map = None
        self._selected_voice_pad_index = 0
        self._on_voice_selected = None
        self._voice_press_interceptor = None

    def set_callbacks(self, on_voice_selected, voice_press_interceptor):
        """on_voice_selected(voice); voice_press_interceptor(pad_index) -> True if consumed."""
        self._on_voice_selected = on_voice_selected
        self._voice_press_interceptor = voice_press_interceptor

    def set_voice_matrix(self, voice_matrix):
        self._on_voice_matrix_value.subject = voice_matrix

    def set_drum_map(self, drum_map):
        self._drum_map = drum_map
        self._selected_voice_pad_index = 0
        self.repaint()

    @property
    def drum_map(self):
        return self._drum_map

    @property
    def selected_voice(self):
        if self._drum_map is None:
            return None
        return self._drum_map.voice_at_pad_index(self._selected_voice_pad_index)

    def voice_at_pad_index(self, pad_index):
        if self._drum_map is None:
            return None
        return self._drum_map.voice_at_pad_index(pad_index)

    @listens("value")
    def _on_voice_matrix_value(self, value, column_index, row_index, _is_momentary):
        if value <= 0:
            return
        pad_index = row_index * layout.VOICE_SELECT_COLUMN_COUNT + column_index
        if self._voice_press_interceptor(pad_index):
            return
        voice = self.voice_at_pad_index(pad_index)
        if voice is None:
            return  # an unused pad (dark): the map has fewer than 16 voices
        self._selected_voice_pad_index = pad_index
        self._on_voice_selected(voice)
        self.repaint()

    def _pad_colour(self, pad_index, super_held):
        if self._drum_map is None:
            return palette.DRUM_NO_MATCHING_DRUM_MAP
        if self._drum_map.voice_at_pad_index(pad_index) is None:
            return palette.OFF
        if super_held:
            return palette.DRUM_SUPER_VOICE_CLEAR
        if pad_index == self._selected_voice_pad_index:
            return palette.DRUM_VOICE_SELECTED
        return palette.DRUM_VOICE_AVAILABLE

    def repaint(self):
        if not self.is_enabled():
            return  # a disabled page never paints; drum_page.repaint_page() runs on entry
        super_held = self._is_super_held()
        self._led_painter.paint([
            (grid_note, self._pad_colour(pad_index, super_held))
            for pad_index, grid_note in enumerate(layout.VOICE_INDEX_TO_GRID_NOTE)
        ])
