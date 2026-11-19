# -*- coding: utf-8 -*-
"""Sonic Charge Microtonic factory key map, standard MIDI mode. Data only.

PURE PYTHON. Source: knowledge_base/plugins/sonic_charge_microtonic/notes.md
(Microtonic_User_Guide p.33, table L1419-1441): notes 36..43 trigger drum channels 1..8.

Assumes the factory key map. The plugin's Receive Channel must be "any" or 1 (the guide does
not state the factory default), and pitched MIDI mode must NOT be used (in pitched mode this
table only responds on MIDI channel 10). Voices are generic drum channels, labelled Ch1..Ch8;
what each sounds like depends on the patch. Covers the single-output plugin and the
multi-output variant (MicrotonicMulti).
"""

from __future__ import absolute_import, print_function, unicode_literals

NAME = "Microtonic"
DEVICE_NAMES = ("Microtonic", "MicrotonicMulti")

MICROTONIC_FIRST_DRUM_CHANNEL_NOTE = 36
MICROTONIC_DRUM_CHANNEL_COUNT = 8

VOICES = tuple(
    ("Ch{0}".format(channel_number), MICROTONIC_FIRST_DRUM_CHANNEL_NOTE + channel_number - 1, ())
    for channel_number in range(1, MICROTONIC_DRUM_CHANNEL_COUNT + 1)
)
