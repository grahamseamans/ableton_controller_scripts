# -*- coding: utf-8 -*-
"""LPX Script: the Launchpad X as a three-page composition controller (launchpad/docs/).

  Session (CC95) -> session page    Note (CC96) -> drum page    Custom (CC97) -> snapshot page
  Capture MIDI (CC98) -> super (momentary hold)

Lifecycle (proven in the archived Jomox script): the framework's identity handshake calls
on_identified, which puts the device in Programmer mode; disconnect() returns it to Live mode.

Pages are the modes of one ModesComponent ("Pages"). Each mode enters, in order:
  1. clear the page LEDs (grid + right column + arrows, 76 LEDs, one batch),
  2. enable the page's components,
  3. give each component its elements through a LayerMode (a disabled page holds no
     elements, so its listeners never see another page's presses),
  4. repaint the page (last, because a Layer grab resets its elements to 0).
Page buttons, super and the logo belong to GlobalControlsComponent, which is always on and
never in a page Layer. The script always opens on the session page.
"""

from __future__ import absolute_import, print_function, unicode_literals

import logging

from ableton.v2.control_surface import IdentifiableControlSurface, Layer
from ableton.v2.control_surface.components import SessionRingComponent
from ableton.v2.control_surface.mode import EnablingMode, LayerMode, Mode, ModesComponent

from . import layout
from . import palette
from .drum_page import DrumPageComponent
from .elements import LpxElements
from .global_controls import (
    DRUM_PAGE_NAME,
    SESSION_PAGE_NAME,
    SNAPSHOT_PAGE_NAME,
    GlobalControlsComponent,
)
from .led import LedPainter
from .session_page import (
    SESSION_RING_HEIGHT_IN_SCENES,
    SESSION_RING_WIDTH_IN_TRACKS,
    SessionPageComponent,
)
from .snapshot_page import SnapshotPageComponent

logger = logging.getLogger(__name__)


class CallOnEnterMode(Mode):
    """A mode step that just calls a function when the page is entered."""

    def __init__(self, function_to_call, *a, **k):
        super(CallOnEnterMode, self).__init__(*a, **k)
        self._function_to_call = function_to_call

    def enter_mode(self):
        self._function_to_call()


class LpxScript(IdentifiableControlSurface):

    def __init__(self, *a, **k):
        super(LpxScript, self).__init__(*a, product_id_bytes=layout.LPX_PRODUCT_ID_BYTES, **k)
        with self.component_guard():
            self._elements = LpxElements()
            self._led_painter = LedPainter(send_sysex_message=self._send_midi)
            self._page_modes = ModesComponent(name="Pages", is_enabled=False)
            self._global_controls = GlobalControlsComponent(
                led_painter=self._led_painter,
                page_modes=self._page_modes,
                elements=self._elements,
                name="Global_Controls",
            )
            self._repaint_page_by_page_name = {}
            self._create_session_page()
            self._create_drum_page()
            self._create_snapshot_page()
            self._page_modes.set_enabled(True)
            self._page_modes.selected_mode = SESSION_PAGE_NAME

    # ---- device mode --------------------------------------------------------------------

    def on_identified(self, midi_bytes):
        logger.info("LPX Script: Launchpad X identified, entering Programmer mode")
        self._elements.firmware_mode_switch.send_value(layout.LPX_PROGRAMMER_MODE_VALUE_BYTE)
        self._global_controls.repaint()
        self._clear_page_leds()
        self._repaint_page_by_page_name[self._page_modes.selected_mode]()
        super(LpxScript, self).on_identified(midi_bytes)

    def disconnect(self):
        # Leave the page first, so its (and the global) LED writes happen while the device
        # is still in Programmer mode, then hand the device back in Live mode.
        self._page_modes.set_enabled(False)
        self._elements.firmware_mode_switch.send_value(layout.LPX_LIVE_MODE_VALUE_BYTE)
        super(LpxScript, self).disconnect()

    # ---- pages --------------------------------------------------------------------------

    def _clear_page_leds(self):
        self._led_painter.paint([(led_index, palette.OFF) for led_index in layout.PAGE_OWNED_LED_INDICES])

    def _add_page(self, page_name, components, component_layers, repaint_page):
        self._repaint_page_by_page_name[page_name] = repaint_page
        self._page_modes.add_mode(
            page_name,
            [CallOnEnterMode(self._clear_page_leds)]
            + [EnablingMode(component) for component in components]
            + [LayerMode(component, layer) for component, layer in component_layers]
            + [CallOnEnterMode(repaint_page)],
        )

    def _create_session_page(self):
        self._session_ring = SessionRingComponent(
            num_tracks=SESSION_RING_WIDTH_IN_TRACKS,
            num_scenes=SESSION_RING_HEIGHT_IN_SCENES,
            name="Session_Ring",
            is_enabled=False,
        )
        self._session_page = SessionPageComponent(
            led_painter=self._led_painter,
            global_controls=self._global_controls,
            session_ring=self._session_ring,
            name="Session_Page",
            is_enabled=False,
        )
        self._add_page(
            SESSION_PAGE_NAME,
            components=(self._session_ring, self._session_page),
            component_layers=((self._session_page, Layer(
                clip_launch_matrix=self._elements.grid_matrix,
                scene_launch_matrix=self._elements.right_column_matrix,
                up_button=self._elements.up_button,
                down_button=self._elements.down_button,
                left_button=self._elements.left_button,
                right_button=self._elements.right_button,
            )),),
            repaint_page=self._session_page.repaint_page,
        )

    def _create_drum_page(self):
        self._drum_page = DrumPageComponent(
            led_painter=self._led_painter,
            global_controls=self._global_controls,
            name="Drum_Page",
            is_enabled=False,
        )
        drum_page = self._drum_page
        self._add_page(
            DRUM_PAGE_NAME,
            components=(drum_page, drum_page.sequencer, drum_page.voice_select, drum_page.pattern_select),
            component_layers=(
                (drum_page.sequencer, Layer(step_matrix=self._elements.step_matrix)),
                (drum_page.voice_select, Layer(voice_matrix=self._elements.voice_matrix)),
                (drum_page.pattern_select, Layer(pattern_matrix=self._elements.pattern_matrix)),
                (drum_page, Layer(
                    velocity_matrix=self._elements.right_column_matrix,
                    length_button=self._elements.up_button,
                    resolution_button=self._elements.down_button,
                    nudge_left_button=self._elements.left_button,
                    nudge_right_button=self._elements.right_button,
                )),
            ),
            repaint_page=drum_page.repaint_page,
        )

    def _create_snapshot_page(self):
        self._snapshot_page = SnapshotPageComponent(
            led_painter=self._led_painter,
            global_controls=self._global_controls,
            name="Snapshot_Page",
            is_enabled=False,
        )
        self._add_page(
            SNAPSHOT_PAGE_NAME,
            components=(self._snapshot_page,),
            component_layers=((self._snapshot_page, Layer(snapshot_matrix=self._elements.grid_matrix)),),
            repaint_page=self._snapshot_page.repaint_page,
        )
