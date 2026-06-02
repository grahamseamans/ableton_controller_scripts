from __future__ import absolute_import, print_function, unicode_literals

import logging

from ableton.v2.base import const, inject, listens, listens_group
from ableton.v2.control_surface import ControlSurface, Layer
from ableton.v2.control_surface.components import (
    MixerComponent,
    SessionRingComponent,
    SimpleTrackAssigner,
)

from .mx12_cc_layout import MX12_NUMBER_OF_TRACKS
from .mx12_elements import MX12Elements


logger = logging.getLogger(__name__)


class _TrackBooleanToggleButtonRowBinder(object):
    # Fires on EVERY incoming value (not just rising edge), because the MX12's
    # buttons are factory-programmed in toggle mode: each physical press sends
    # a single CC value alternating 127/0. Treating each value-change as one
    # toggle gives the user single-tap behavior.
    def __init__(self, live_song, button_elements_by_track_index, track_attribute_name, name):
        self._live_song = live_song
        self._button_elements_by_track_index = button_elements_by_track_index
        self._track_attribute_name = track_attribute_name
        self._name = name
        self._button_value_listener_by_track_index = [None] * MX12_NUMBER_OF_TRACKS
        for track_index, button_element in enumerate(button_elements_by_track_index):
            value_listener = self._make_button_value_listener_for_track_index(track_index)
            self._button_value_listener_by_track_index[track_index] = value_listener
            button_element.add_value_listener(value_listener)

    def _make_button_value_listener_for_track_index(self, track_index):
        def on_button_value_changed(_midi_value_0_to_127):
            live_tracks = list(self._live_song.tracks)
            if track_index >= len(live_tracks):
                return
            target_track = live_tracks[track_index]
            if not hasattr(target_track, self._track_attribute_name):
                return
            current_value = getattr(target_track, self._track_attribute_name)
            setattr(target_track, self._track_attribute_name, not current_value)

        return on_button_value_changed

    def disconnect(self):
        for track_index, button_element in enumerate(self._button_elements_by_track_index):
            value_listener = self._button_value_listener_by_track_index[track_index]
            if value_listener is not None:
                button_element.remove_value_listener(value_listener)


class MX12Surface(ControlSurface):
    __doc__ = u"Faderfox MX12 mixing surface (factory generic setup 1, channel 1)"
    __name__ = u"Faderfox MX12 Mixer"

    def __init__(self, c_instance, *a, **k):
        super(MX12Surface, self).__init__(c_instance=c_instance, *a, **k)
        self._create_elements()
        self._create_components()
        self._create_solo_and_mute_button_binders()
        self._install_track_state_listeners_for_led_feedback()
        self._refresh_all_button_leds_from_live_state()
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
            pan_controls=u"track_pan_pot_row_b_compound",
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

    def _create_solo_and_mute_button_binders(self):
        live_song = self.song
        self._track_solo_button_row_binder = _TrackBooleanToggleButtonRowBinder(
            live_song,
            self._elements.track_solo_gray_button_elements_list,
            u"solo",
            u"MX12_Solo",
        )
        self._track_mute_button_row_binder = _TrackBooleanToggleButtonRowBinder(
            live_song,
            self._elements.track_mute_green_button_elements_list,
            u"mute",
            u"MX12_Mute",
        )

    def _install_track_state_listeners_for_led_feedback(self):
        self._on_song_tracks_changed.subject = self.song
        self._refresh_per_track_state_listener_subjects()

    def _refresh_per_track_state_listener_subjects(self):
        live_tracks = list(self.song.tracks)
        self._on_any_track_mute_changed.replace_subjects(live_tracks)
        self._on_any_track_solo_changed.replace_subjects(live_tracks)

    @listens(u"tracks")
    def _on_song_tracks_changed(self):
        self._refresh_per_track_state_listener_subjects()
        self._refresh_all_button_leds_from_live_state()

    @listens_group(u"mute")
    def _on_any_track_mute_changed(self, changed_track):
        self._send_mute_led_for_changed_track(changed_track)

    @listens_group(u"solo")
    def _on_any_track_solo_changed(self, changed_track):
        self._send_solo_led_for_changed_track(changed_track)

    def _send_mute_led_for_changed_track(self, changed_track):
        track_index = self._find_track_index_for_track(changed_track)
        if track_index is None:
            return
        button_element = self._elements.track_mute_green_button_elements_list[track_index]
        button_element.send_value(127 if changed_track.mute else 0)

    def _send_solo_led_for_changed_track(self, changed_track):
        track_index = self._find_track_index_for_track(changed_track)
        if track_index is None:
            return
        button_element = self._elements.track_solo_gray_button_elements_list[track_index]
        button_element.send_value(127 if changed_track.solo else 0)

    def _find_track_index_for_track(self, target_track):
        for track_index, candidate_track in enumerate(self.song.tracks):
            if candidate_track is target_track and track_index < MX12_NUMBER_OF_TRACKS:
                return track_index
        return None

    def _refresh_all_button_leds_from_live_state(self):
        live_tracks = list(self.song.tracks)
        for track_index in range(MX12_NUMBER_OF_TRACKS):
            mute_button_element = self._elements.track_mute_green_button_elements_list[track_index]
            solo_button_element = self._elements.track_solo_gray_button_elements_list[track_index]
            if track_index < len(live_tracks):
                target_track = live_tracks[track_index]
                mute_button_element.send_value(127 if target_track.mute else 0)
                solo_button_element.send_value(127 if target_track.solo else 0)
            else:
                mute_button_element.send_value(0)
                solo_button_element.send_value(0)

    def disconnect(self):
        solo_binder = getattr(self, "_track_solo_button_row_binder", None)
        mute_binder = getattr(self, "_track_mute_button_row_binder", None)
        if solo_binder is not None:
            solo_binder.disconnect()
        if mute_binder is not None:
            mute_binder.disconnect()
        super(MX12Surface, self).disconnect()

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
