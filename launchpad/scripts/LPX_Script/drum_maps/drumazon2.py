# -*- coding: utf-8 -*-
"""D16 Drumazon 2 factory (GM-style) drum map. Data only; drum_maps/__init__.py builds it.

PURE PYTHON. Source: knowledge_base/plugins/d16_drumazon/notes.md (Drumazon2-manual-gb p.30-31).

UNVERIFIED: the manual has no numeric table. These notes were read off the Drum Map
screenshot on p.31 ASSUMING the screenshot's C0 = MIDI 24 (our inference, consistent with GM
and with Live's naming where 36 = C1). Assumes the plugin's factory map; a user map breaks
this. The manual does not document Drumazon's MIDI channel behaviour. Verify in Live
(launchpad/SHORTCUTS.md).
"""

from __future__ import absolute_import, print_function, unicode_literals

NAME = "Drumazon 2"
DEVICE_NAMES = ("Drumazon 2",)

# (voice name, note written, also-matching notes read as the same lane), pad order.
VOICES = (
    ("BD", 36, (35,)),
    ("RS", 37, ()),
    ("SD", 38, (40,)),
    ("CP", 39, ()),
    ("LT", 41, (43,)),
    ("CH", 42, (44,)),
    ("MT", 45, (47,)),
    ("OH", 46, ()),
    ("HT", 48, (50,)),
    ("CR", 49, ()),
    ("RD", 51, ()),
)
