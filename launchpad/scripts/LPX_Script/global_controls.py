# -*- coding: utf-8 -*-
"""Always-on controls: the three page buttons, super (Capture MIDI), and their LEDs + logo.

Never part of a page Layer; its buttons are bound directly with `.subject`, which is safe
because no page ever claims them. Pages subscribe to `super_held` and repaint the pads whose
meaning changes; a page with no super action ignores it.
"""

from __future__ import absolute_import, print_function, unicode_literals

import logging

from ableton.v2.base import listenable_property, listens
from ableton.v2.control_surface import Component

from . import layout
from . import palette

logger = logging.getLogger(__name__)

SESSION_PAGE_NAME = "session"
DRUM_PAGE_NAME = "drums"
SNAPSHOT_PAGE_NAME = "snapshots"
PAGE_NAMES = (SESSION_PAGE_NAME, DRUM_PAGE_NAME, SNAPSHOT_PAGE_NAME)

PAGE_BUTTON_CC_NUMBER_BY_PAGE_NAME = {
    SESSION_PAGE_NAME: layout.SESSION_BUTTON_CC_NUMBER,
    DRUM_PAGE_NAME: layout.NOTE_BUTTON_CC_NUMBER,
    SNAPSHOT_PAGE_NAME: layout.CUSTOM_BUTTON_CC_NUMBER,
}


class GlobalControlsComponent(Component):

    def __init__(self, led_painter=None, page_modes=None, elements=None, *a, **k):
        super(GlobalControlsComponent, self).__init__(*a, **k)
        if led_painter is None or page_modes is None or elements is None:
            raise ValueError("GlobalControlsComponent needs led_painter, page_modes and elements")
        self._led_painter = led_painter
        self._page_modes = page_modes
        self._super_held = False
        self._on_session_page_button_value.subject = elements.session_page_button
        self._on_drum_page_button_value.subject = elements.drum_page_button
        self._on_snapshot_page_button_value.subject = elements.snapshot_page_button
        self._on_super_button_value.subject = elements.super_button
        self._on_selected_page_changed.subject = page_modes

    @listenable_property
    def super_held(self):
        return self._super_held

    # ---- page buttons -------------------------------------------------------------------

    def _select_page(self, page_name):
        logger.info("LPX Script: page -> %s", page_name)
        self._page_modes.selected_mode = page_name

    @listens("value")
    def _on_session_page_button_value(self, value):
        if value > 0:
            self._select_page(SESSION_PAGE_NAME)

    @listens("value")
    def _on_drum_page_button_value(self, value):
        if value > 0:
            self._select_page(DRUM_PAGE_NAME)

    @listens("value")
    def _on_snapshot_page_button_value(self, value):
        if value > 0:
            self._select_page(SNAPSHOT_PAGE_NAME)

    @listens("selected_mode")
    def _on_selected_page_changed(self, _selected_page_name):
        self.repaint()

    # ---- super (momentary hold) ---------------------------------------------------------

    @listens("value")
    def _on_super_button_value(self, value):
        is_held = value > 0
        if is_held == self._super_held:
            return
        self._super_held = is_held
        self.repaint()
        self.notify_super_held(is_held)

    # ---- LEDs ---------------------------------------------------------------------------

    def repaint(self):
        selected_page_name = self._page_modes.selected_mode
        leds = []
        for page_name in PAGE_NAMES:
            leds.append((
                PAGE_BUTTON_CC_NUMBER_BY_PAGE_NAME[page_name],
                palette.page_button_colour(page_name, page_name == selected_page_name),
            ))
        leds.append((layout.CAPTURE_MIDI_BUTTON_CC_NUMBER,
                     palette.SUPER_HELD if self._super_held else palette.SUPER_AT_REST))
        if selected_page_name is None:
            leds.append((layout.LOGO_CC_NUMBER, palette.OFF))
        else:
            leds.append((layout.LOGO_CC_NUMBER, palette.PAGE_SIGNATURE_BY_PAGE_NAME[selected_page_name]))
        self._led_painter.paint(leds)
