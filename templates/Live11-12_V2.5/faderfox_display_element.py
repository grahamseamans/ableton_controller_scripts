from __future__ import absolute_import, print_function, unicode_literals
import logging
from typing import List
from ableton.v2.base import liveobj_valid
from ableton.v2.control_surface import ControlElement
from ableton.v2.control_surface.elements import PhysicalDisplayElement, DisplayElement, DisplayDataSource
from .consts import *

logger = logging.getLogger(__name__)

def get_message_header(offset: int):
    charoffset = offset * 4
    return (
        (SYSEX_START_BYTE, 0, 0, 0)
        + FADERFOX_EC4_DEVICE_ID
        + SET_TEXT_MSG_HEADER
        + (0x4A, 0x20 | (charoffset >> 4), 0x10 | (charoffset & 0xF))
    )

def get_item(lst, index, default):
    if 0 <= index < len(lst):
        return lst[index]
    else:
        return default

class FaderfoxPartDisplayElement(DisplayElement):
    def __init__(self, parent, id, map, *a, **k):
        super(FaderfoxPartDisplayElement, self).__init__(width_in_chars=(NUM_DISPLAY_LINE_SEGMENTS * 4), num_segments=len(map), *a, **k)
        self._parent = parent
        self._id = id
        self._map = map

    def set_values(self, values):
        for ix in range(len(self._map)):
            self.set_value(ix, values[ix] if ix < len(values) else u'')
        self._parent.update()

    def set_value(self, ix, value):
        if ix >= len(self._map):
            return

        for setup, group, index in self._map[ix]:
            #logger.info(u'Faderfox Universal 2: Setting display value for setup {}, group {}, index {} to {}'.format(setup, group, index, value))
            self._parent._cells[setup][group][index] = value

    def update(self):
        for segment, ix in zip(self._logical_segments, range(len(self._logical_segments))):
            self.set_value(ix, segment.display_string());
        self._parent.update()


class FaderfoxDisplayElement(PhysicalDisplayElement):
    _enabled = True
    _current_group = (0, 0)

    def add_part(self, map):
        return FaderfoxPartDisplayElement(self, id, map)

    def set_group(self, group):
        self._current_group = group
        self.update()

    def __init__(self, enabled=True, *a, **k):
        self._cells = [[[u'' for _ in range(NUM_DISPLAY_LINE_SEGMENTS)] for g in range(GROUP_COUNT)] for s in range(SETUP_COUNT)]
        self._ds = [DisplayDataSource(u'') for _ in range(NUM_DISPLAY_LINE_SEGMENTS)]
        super(FaderfoxDisplayElement, self).__init__(
            width_in_chars=(NUM_DISPLAY_LINE_SEGMENTS * 4), num_segments=NUM_DISPLAY_LINE_SEGMENTS, *a, **k
        )
        self._enabled = enabled
        self.set_data_sources(self._ds)
        self.set_message_parts(get_message_header(0), (SYSEX_END_BYTE,))

    def _translate_string(self, string):
        text = super(FaderfoxDisplayElement, self)._translate_string(string)
        return [
            item for c in text for item in [0x4D, 0x20 | (c >> 4), 0x10 | (c & 0xF)]
        ]

    def set_enabled(self, value):
        #logger.info("Setting faderfox Universal 2 DISPLAY enabled to {}".format(value))
        if self._enabled == value:
            return

        self._enabled = value
        if value:
            self.update()
    
    def send_midi(self, midi_bytes):
        if self._current_group[0] not in DEVICE_DISPLAY_SETUPS:
            return
        #logger.info("Sending faderfox Universal 2 DISPLAY midi bytes: {}".format(midi_bytes))
        super(FaderfoxDisplayElement, self).send_midi(midi_bytes)

    def update(self):
        if not self._enabled:
            return

        values = self._cells[self._current_group[0]][self._current_group[1]]
        if values.count(u'') == len(values):
            return

        #logger.info("Upating faderfox Universal 2: Values for ({}): {}".format(self._current_group, values))
        self.set_block_messages(True)
        for ix in range(self.num_segments):
            self._ds[ix].set_display_string(values[ix])
        self.set_block_messages(False)

        super(FaderfoxDisplayElement, self).update()

    def reset(self):
        self.send_midi(CLEAR_MAIN_DISPLAY)

