from __future__ import absolute_import, print_function, unicode_literals
import logging

logger = logging.getLogger(__name__)

def create_instance(c_instance):
    from .FaderfoxSurface import FaderfoxSurface
    return FaderfoxSurface(c_instance)

'''
def get_capabilities():
    from ableton.v2.control_surface import capabilities as caps
    return {caps.CONTROLLER_ID_KEY: caps.controller_id(vendor_id=2256, product_ids=[2010], model_name=u'Faderfox Universal'),
     caps.PORTS_KEY: [caps.inport(props=[caps.HIDDEN, caps.NOTES_CC, caps.SCRIPT]),
                      caps.inport(props=[]),
                      caps.outport(props=[caps.HIDDEN,
                       caps.NOTES_CC,
                       caps.SYNC,
                       caps.SCRIPT]),
                      caps.outport(props=[])],
     #caps.TYPE_KEY: u'push2',
     caps.AUTO_LOAD_KEY: True}

from _Framework.Capabilities import *

def get_capabilities():
    return {CONTROLLER_ID_KEY: controller_id(vendor_id=2256, product_ids=[2010], model_name=u'Faderfox Universal'),
     PORTS_KEY: [inport(props=[NOTES_CC, REMOTE, SCRIPT]), outport(props=[SCRIPT])]}
'''
