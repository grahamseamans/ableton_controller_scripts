from __future__ import absolute_import, print_function, unicode_literals
import logging
from ableton.v2.control_surface import ControlElement, midi

logger = logging.getLogger(__name__)

class PitchBendElement(ControlElement):
    def __init__(self, channel, *a, **k):
        super(PitchBendElement, self).__init__(self, *a, **k)
        self._channel = channel

    def send_value(self, value):
        self.send_midi((midi.PB_STATUS | self._channel, value & 0x7F, (value >> 7) & 0x7F))

    def reset(self):
        pass
