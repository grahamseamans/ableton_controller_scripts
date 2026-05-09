from __future__ import absolute_import, print_function, unicode_literals

import logging

from ableton.v2.base import const, inject, listens
from ableton.v2.control_surface import ControlSurface, Layer
from ableton.v2.control_surface.components import (
    MixerComponent,
    SessionRingComponent,
    SimpleTrackAssigner,
)

from .mx12_cc_layout import MX12_NUMBER_OF_TRACKS
from .mx12_elements import MX12Elements


logger = logging.getLogger(__name__)


class MX12Surface(ControlSurface):
    __doc__ = u"Faderfox MX12 mixing surface (factory generic setup 1, channel 1)"
    __name__ = u"Faderfox MX12 Mixer"

    def __init__(self, c_instance, *a, **k):
        super(MX12Surface, self).__init__(c_instance=c_instance, *a, **k)
        self._create_elements()
        self._create_components()
        self.show_message(u"{} loaded".format(self.__name__))

    def _create_elements(self):
        with self.component_guard():
            self._elements = MX12Elements()

    def _create_components(self):
        # element_container injection is required for Layer string-name resolution.
        # Passing element instances directly to Layer in Live 12.4's v2 API silently
        # fails to bind to MixerComponent slots like volume_controls / pan_controls.
        with self.component_guard():
            with inject(element_container=const(self._elements)).everywhere():
                self._create_mixer()
                self._bind_scene_select_encoder()
                self._bind_scene_launch_button()

    def _create_mixer(self):
        self._session_ring_component = SessionRingComponent(
            is_enabled=False,
            num_tracks=MX12_NUMBER_OF_TRACKS,
            tracks_to_use=lambda: tuple(self.song.tracks),
            name=u"MX12_Session_Ring",
        )

        mixer_layer = Layer(
            volume_controls=u"track_volume_fader_compound",
            pan_controls=u"track_pan_pot_row_a_compound",
            solo_buttons=u"track_solo_gray_button_compound",
            mute_buttons=u"track_mute_green_button_compound",
        )

        self._mixer_component = MixerComponent(
            is_enabled=False,
            tracks_provider=self._session_ring_component,
            track_assigner=SimpleTrackAssigner(),
            name=u"MX12_Mixer",
            layer=mixer_layer,
        )
        self._mixer_component.set_enabled(True)

    def _bind_scene_select_encoder(self):
        self._on_scene_select_encoder_value.subject = self._elements.scene_select_encoder

    def _bind_scene_launch_button(self):
        self._on_scene_launch_button_value.subject = self._elements.scene_launch_push_button

    def process_midi_bytes(self, midi_bytes, midi_processor):
        if len(midi_bytes) >= 3:
            channel_one_based = (midi_bytes[0] & 0x0F) + 1
            status_nibble = midi_bytes[0] & 0xF0
            kind_label = {
                0xB0: u"CC",
                0x90: u"NoteOn",
                0x80: u"NoteOff",
                0xE0: u"PB",
            }.get(status_nibble, u"0x{:02X}".format(status_nibble))
            logger.info(
                u"MX12 MIDI RX  ch={:2d}  {:7s}  d1={:3d}  d2={:3d}".format(
                    channel_one_based, kind_label, midi_bytes[1], midi_bytes[2]
                )
            )
        super(MX12Surface, self).process_midi_bytes(midi_bytes, midi_processor)

    @listens(u"value")
    def _on_scene_select_encoder_value(self, encoder_value):
        live_song = self.song
        scene_count = len(live_song.scenes)
        if scene_count == 0:
            return
        target_scene_index = int(encoder_value * (scene_count - 1) / 127)
        live_song.view.selected_scene = live_song.scenes[target_scene_index]

    @listens(u"value")
    def _on_scene_launch_button_value(self, button_value):
        if button_value <= 0:
            return
        selected_scene = self.song.view.selected_scene
        if selected_scene is None:
            return
        selected_scene.fire()
