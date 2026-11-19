# -*- coding: utf-8 -*-
"""Package entry point for the LPX Script Live remote script (Launchpad X, Programmer mode).

get_capabilities lets Live auto-detect the Launchpad X and bind its "LPX MIDI" ports; the
script drives the device in Programmer mode with plain Note/CC, not the DAW protocol.
"""

from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.control_surface.capabilities import (
    CONTROLLER_ID_KEY,
    NOTES_CC,
    PORTS_KEY,
    controller_id,
    inport,
    outport,
)

from .surface import LpxScript


def get_capabilities():
    # Launchpad X USB vendor id 4661 (0x1235), product id 259 (0x0103), per the stock script.
    return {
        CONTROLLER_ID_KEY: controller_id(
            vendor_id=4661, product_ids=[259], model_name=["Launchpad X"]
        ),
        PORTS_KEY: [
            inport(props=[NOTES_CC]),
            outport(props=[NOTES_CC]),
        ],
    }


def create_instance(c_instance):
    return LpxScript(c_instance=c_instance)
