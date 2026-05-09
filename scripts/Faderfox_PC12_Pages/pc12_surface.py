from __future__ import absolute_import, print_function, unicode_literals

import logging

import Live

from ableton.v2.base import listens, listens_group
from ableton.v2.control_surface import ControlSurface, MIDI_CC_TYPE
from ableton.v2.control_surface.elements import ButtonElement, EncoderElement

from .pc12_cc_layout import (
    PC12_NUMBER_OF_TRACKS,
    PC12_MIDI_CHANNEL_INDEX_PERFORMANCE_PAGE,
    PC12_MIDI_CHANNEL_INDEX_COMPRESSION_PAGE,
    PC12_MIDI_CHANNEL_INDEX_EQ_PAGE,
    PC12_POT_ROW_A_CC_BASE,
    PC12_POT_ROW_B_CC_BASE,
    PC12_POT_ROW_C_CC_BASE,
    PC12_POT_ROW_D_CC_BASE,
    PC12_POT_ROW_E_CC_BASE,
    PC12_POT_ROW_F_CC_BASE,
    PC12_GREEN_BUTTON_CC_BASE,
)

from .page_performance import (
    find_filter_eq_high_pass_frequency_parameter_for_track,
    find_filter_eq_low_pass_frequency_parameter_for_track,
)
from .page_compression import (
    find_compressor_threshold_parameter_for_track,
    find_compressor_ratio_parameter_for_track,
    find_compressor_attack_parameter_for_track,
    find_compressor_release_parameter_for_track,
    find_compressor_knee_parameter_for_track,
    find_compressor_output_gain_parameter_for_track,
    find_compressor_device_for_track,
)
from .page_eq import (
    find_tonal_eq_band_1_gain_parameter_for_track,
    find_tonal_eq_band_1_frequency_parameter_for_track,
    find_tonal_eq_band_2_gain_parameter_for_track,
    find_tonal_eq_band_2_frequency_parameter_for_track,
    find_tonal_eq_band_3_gain_parameter_for_track,
    find_tonal_eq_band_3_frequency_parameter_for_track,
    find_tonal_eq_eight_device_for_track,
)


logger = logging.getLogger(__name__)


def _build_per_track_encoder_row(midi_channel_index, cc_base, name_prefix):
    return [
        EncoderElement(
            MIDI_CC_TYPE,
            midi_channel_index,
            cc_base + track_index,
            Live.MidiMap.MapMode.absolute,
            name=u"{}_{}".format(name_prefix, track_index + 1),
        )
        for track_index in range(PC12_NUMBER_OF_TRACKS)
    ]


def _build_per_track_button_row(midi_channel_index, cc_base, name_prefix):
    return [
        ButtonElement(
            True,
            MIDI_CC_TYPE,
            midi_channel_index,
            cc_base + track_index,
            name=u"{}_{}".format(name_prefix, track_index + 1),
        )
        for track_index in range(PC12_NUMBER_OF_TRACKS)
    ]


def find_send_parameter_finder_factory_for_send_index(send_index_zero_based):
    def find_send_parameter_for_track(live_track):
        track_sends = live_track.mixer_device.sends
        if send_index_zero_based >= len(track_sends):
            return None
        return track_sends[send_index_zero_based]
    return find_send_parameter_for_track


class _DirectParameterEncoderRowBinder(object):
    def __init__(
        self,
        live_song,
        encoder_elements_by_track_index,
        per_track_parameter_finder,
        name,
    ):
        self._live_song = live_song
        self._encoder_elements_by_track_index = encoder_elements_by_track_index
        self._per_track_parameter_finder = per_track_parameter_finder
        self._name = name
        self._currently_bound_parameter_by_track_index = [None] * PC12_NUMBER_OF_TRACKS
        self._encoder_value_listener_by_track_index = [None] * PC12_NUMBER_OF_TRACKS
        for track_index, encoder_element in enumerate(self._encoder_elements_by_track_index):
            value_listener = self._make_encoder_value_listener_for_track_index(track_index)
            self._encoder_value_listener_by_track_index[track_index] = value_listener
            encoder_element.add_value_listener(value_listener)

    def _make_encoder_value_listener_for_track_index(self, track_index):
        def on_encoder_value_changed(midi_value_0_to_127):
            target_parameter = self._currently_bound_parameter_by_track_index[track_index]
            if target_parameter is None:
                return
            parameter_minimum_value = target_parameter.min
            parameter_maximum_value = target_parameter.max
            normalized_zero_to_one = midi_value_0_to_127 / 127.0
            target_parameter.value = parameter_minimum_value + normalized_zero_to_one * (
                parameter_maximum_value - parameter_minimum_value
            )

        return on_encoder_value_changed

    def rebind_to_current_tracks(self):
        live_tracks = list(self._live_song.tracks)
        for track_index in range(PC12_NUMBER_OF_TRACKS):
            if track_index < len(live_tracks):
                self._currently_bound_parameter_by_track_index[track_index] = (
                    self._per_track_parameter_finder(live_tracks[track_index])
                )
            else:
                self._currently_bound_parameter_by_track_index[track_index] = None

    def disconnect(self):
        for track_index, encoder_element in enumerate(self._encoder_elements_by_track_index):
            value_listener = self._encoder_value_listener_by_track_index[track_index]
            if value_listener is not None:
                encoder_element.remove_value_listener(value_listener)
        self._currently_bound_parameter_by_track_index = [None] * PC12_NUMBER_OF_TRACKS


class _DeviceOnOffButtonRowBinder(object):
    def __init__(
        self,
        live_song,
        button_elements_by_track_index,
        per_track_device_finder,
        name,
    ):
        self._live_song = live_song
        self._button_elements_by_track_index = button_elements_by_track_index
        self._per_track_device_finder = per_track_device_finder
        self._name = name
        self._currently_bound_device_by_track_index = [None] * PC12_NUMBER_OF_TRACKS
        self._button_value_listener_by_track_index = [None] * PC12_NUMBER_OF_TRACKS
        for track_index, button_element in enumerate(self._button_elements_by_track_index):
            value_listener = self._make_button_value_listener_for_track_index(track_index)
            self._button_value_listener_by_track_index[track_index] = value_listener
            button_element.add_value_listener(value_listener)

    def _make_button_value_listener_for_track_index(self, track_index):
        def on_button_value_changed(midi_value_0_to_127):
            if midi_value_0_to_127 <= 0:
                return
            target_device = self._currently_bound_device_by_track_index[track_index]
            if target_device is None:
                return
            target_device.is_active = not target_device.is_active

        return on_button_value_changed

    def rebind_to_current_tracks(self):
        live_tracks = list(self._live_song.tracks)
        for track_index in range(PC12_NUMBER_OF_TRACKS):
            if track_index < len(live_tracks):
                self._currently_bound_device_by_track_index[track_index] = (
                    self._per_track_device_finder(live_tracks[track_index])
                )
            else:
                self._currently_bound_device_by_track_index[track_index] = None

    def disconnect(self):
        for track_index, button_element in enumerate(self._button_elements_by_track_index):
            value_listener = self._button_value_listener_by_track_index[track_index]
            if value_listener is not None:
                button_element.remove_value_listener(value_listener)
        self._currently_bound_device_by_track_index = [None] * PC12_NUMBER_OF_TRACKS


class _TrackArmButtonRowBinder(object):
    def __init__(self, live_song, button_elements_by_track_index, name):
        self._live_song = live_song
        self._button_elements_by_track_index = button_elements_by_track_index
        self._name = name
        self._button_value_listener_by_track_index = [None] * PC12_NUMBER_OF_TRACKS
        for track_index, button_element in enumerate(button_elements_by_track_index):
            value_listener = self._make_button_value_listener_for_track_index(track_index)
            self._button_value_listener_by_track_index[track_index] = value_listener
            button_element.add_value_listener(value_listener)

    def _make_button_value_listener_for_track_index(self, track_index):
        def on_button_value_changed(midi_value_0_to_127):
            if midi_value_0_to_127 <= 0:
                return
            live_tracks = list(self._live_song.tracks)
            if track_index >= len(live_tracks):
                return
            target_track = live_tracks[track_index]
            if not getattr(target_track, "can_be_armed", False):
                return
            target_track.arm = not target_track.arm

        return on_button_value_changed

    def disconnect(self):
        for track_index, button_element in enumerate(self._button_elements_by_track_index):
            value_listener = self._button_value_listener_by_track_index[track_index]
            if value_listener is not None:
                button_element.remove_value_listener(value_listener)


class PC12Surface(ControlSurface):
    __doc__ = u"Faderfox PC12 page surface (Performance / Compression / EQ across channels 1, 2, 3)"
    __name__ = u"Faderfox PC12 Pages"

    def __init__(self, c_instance, *a, **k):
        super(PC12Surface, self).__init__(c_instance=c_instance, *a, **k)
        with self.component_guard():
            self._build_all_elements()
            self._build_all_direct_binders()
            self._install_track_change_listeners()
            self._rebind_all_direct_binders()
        self.show_message(u"{} loaded".format(self.__name__))

    def _build_all_elements(self):
        self._build_performance_page_elements()
        self._build_compression_page_elements()
        self._build_eq_page_elements()

    def _build_performance_page_elements(self):
        ch = PC12_MIDI_CHANNEL_INDEX_PERFORMANCE_PAGE

        self._performance_send_1_pot_row_a_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_A_CC_BASE, u"PC12_Perf_Send1_Pot"
        )
        self._performance_send_2_pot_row_b_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_B_CC_BASE, u"PC12_Perf_Send2_Pot"
        )
        self._performance_send_3_pot_row_c_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_C_CC_BASE, u"PC12_Perf_Send3_Pot"
        )
        self._performance_send_4_pot_row_d_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_D_CC_BASE, u"PC12_Perf_Send4_Pot"
        )
        self._performance_filter_high_pass_pot_row_e_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_E_CC_BASE, u"PC12_Perf_HighPass_Pot"
        )
        self._performance_filter_low_pass_pot_row_f_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_F_CC_BASE, u"PC12_Perf_LowPass_Pot"
        )
        self._performance_track_arm_green_button_elements = _build_per_track_button_row(
            ch, PC12_GREEN_BUTTON_CC_BASE, u"PC12_Perf_Arm_Button"
        )

    def _build_compression_page_elements(self):
        ch = PC12_MIDI_CHANNEL_INDEX_COMPRESSION_PAGE

        self._compression_threshold_pot_row_a_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_A_CC_BASE, u"PC12_Comp_Threshold_Pot"
        )
        self._compression_ratio_pot_row_b_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_B_CC_BASE, u"PC12_Comp_Ratio_Pot"
        )
        self._compression_attack_pot_row_c_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_C_CC_BASE, u"PC12_Comp_Attack_Pot"
        )
        self._compression_release_pot_row_d_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_D_CC_BASE, u"PC12_Comp_Release_Pot"
        )
        self._compression_knee_pot_row_e_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_E_CC_BASE, u"PC12_Comp_Knee_Pot"
        )
        self._compression_output_gain_pot_row_f_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_F_CC_BASE, u"PC12_Comp_OutputGain_Pot"
        )
        self._compression_device_on_off_green_button_elements = _build_per_track_button_row(
            ch, PC12_GREEN_BUTTON_CC_BASE, u"PC12_Comp_OnOff_Button"
        )

    def _build_eq_page_elements(self):
        ch = PC12_MIDI_CHANNEL_INDEX_EQ_PAGE

        self._eq_band_1_gain_pot_row_a_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_A_CC_BASE, u"PC12_EQ_Band1_Gain_Pot"
        )
        self._eq_band_1_frequency_pot_row_b_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_B_CC_BASE, u"PC12_EQ_Band1_Freq_Pot"
        )
        self._eq_band_2_gain_pot_row_c_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_C_CC_BASE, u"PC12_EQ_Band2_Gain_Pot"
        )
        self._eq_band_2_frequency_pot_row_d_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_D_CC_BASE, u"PC12_EQ_Band2_Freq_Pot"
        )
        self._eq_band_3_gain_pot_row_e_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_E_CC_BASE, u"PC12_EQ_Band3_Gain_Pot"
        )
        self._eq_band_3_frequency_pot_row_f_elements = _build_per_track_encoder_row(
            ch, PC12_POT_ROW_F_CC_BASE, u"PC12_EQ_Band3_Freq_Pot"
        )
        self._eq_device_on_off_green_button_elements = _build_per_track_button_row(
            ch, PC12_GREEN_BUTTON_CC_BASE, u"PC12_EQ_OnOff_Button"
        )

    def _build_all_direct_binders(self):
        live_song = self.song

        self._all_direct_parameter_encoder_row_binders = [
            _DirectParameterEncoderRowBinder(
                live_song,
                self._performance_send_1_pot_row_a_elements,
                find_send_parameter_finder_factory_for_send_index(0),
                u"PerfSend1",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._performance_send_2_pot_row_b_elements,
                find_send_parameter_finder_factory_for_send_index(1),
                u"PerfSend2",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._performance_send_3_pot_row_c_elements,
                find_send_parameter_finder_factory_for_send_index(2),
                u"PerfSend3",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._performance_send_4_pot_row_d_elements,
                find_send_parameter_finder_factory_for_send_index(3),
                u"PerfSend4",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._performance_filter_high_pass_pot_row_e_elements,
                find_filter_eq_high_pass_frequency_parameter_for_track,
                u"PerfHighPass",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._performance_filter_low_pass_pot_row_f_elements,
                find_filter_eq_low_pass_frequency_parameter_for_track,
                u"PerfLowPass",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._compression_threshold_pot_row_a_elements,
                find_compressor_threshold_parameter_for_track,
                u"CompThreshold",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._compression_ratio_pot_row_b_elements,
                find_compressor_ratio_parameter_for_track,
                u"CompRatio",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._compression_attack_pot_row_c_elements,
                find_compressor_attack_parameter_for_track,
                u"CompAttack",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._compression_release_pot_row_d_elements,
                find_compressor_release_parameter_for_track,
                u"CompRelease",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._compression_knee_pot_row_e_elements,
                find_compressor_knee_parameter_for_track,
                u"CompKnee",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._compression_output_gain_pot_row_f_elements,
                find_compressor_output_gain_parameter_for_track,
                u"CompOutputGain",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._eq_band_1_gain_pot_row_a_elements,
                find_tonal_eq_band_1_gain_parameter_for_track,
                u"EQBand1Gain",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._eq_band_1_frequency_pot_row_b_elements,
                find_tonal_eq_band_1_frequency_parameter_for_track,
                u"EQBand1Freq",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._eq_band_2_gain_pot_row_c_elements,
                find_tonal_eq_band_2_gain_parameter_for_track,
                u"EQBand2Gain",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._eq_band_2_frequency_pot_row_d_elements,
                find_tonal_eq_band_2_frequency_parameter_for_track,
                u"EQBand2Freq",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._eq_band_3_gain_pot_row_e_elements,
                find_tonal_eq_band_3_gain_parameter_for_track,
                u"EQBand3Gain",
            ),
            _DirectParameterEncoderRowBinder(
                live_song,
                self._eq_band_3_frequency_pot_row_f_elements,
                find_tonal_eq_band_3_frequency_parameter_for_track,
                u"EQBand3Freq",
            ),
        ]

        self._all_device_on_off_button_row_binders = [
            _DeviceOnOffButtonRowBinder(
                live_song,
                self._compression_device_on_off_green_button_elements,
                find_compressor_device_for_track,
                u"CompOnOff",
            ),
            _DeviceOnOffButtonRowBinder(
                live_song,
                self._eq_device_on_off_green_button_elements,
                find_tonal_eq_eight_device_for_track,
                u"EQOnOff",
            ),
        ]

        self._track_arm_button_row_binder = _TrackArmButtonRowBinder(
            live_song,
            self._performance_track_arm_green_button_elements,
            u"PerfArm",
        )

    def _install_track_change_listeners(self):
        self._on_song_tracks_changed.subject = self.song
        self._refresh_per_track_devices_listeners()

    def _refresh_per_track_devices_listeners(self):
        self._on_any_track_devices_changed.replace_subjects(list(self.song.tracks))

    @listens(u"tracks")
    def _on_song_tracks_changed(self):
        self._refresh_per_track_devices_listeners()
        self._rebind_all_direct_binders()

    @listens_group(u"devices")
    def _on_any_track_devices_changed(self, _track):
        self._rebind_all_direct_binders()

    def _rebind_all_direct_binders(self):
        for encoder_row_binder in self._all_direct_parameter_encoder_row_binders:
            encoder_row_binder.rebind_to_current_tracks()
        for button_row_binder in self._all_device_on_off_button_row_binders:
            button_row_binder.rebind_to_current_tracks()

    def process_midi_bytes(self, midi_bytes, midi_processor):
        if len(midi_bytes) >= 1:
            status_byte = midi_bytes[0]
            channel_one_based = (status_byte & 0x0F) + 1
            status_nibble = status_byte & 0xF0
            kind_label = {
                0x80: u"NoteOff",
                0x90: u"NoteOn",
                0xA0: u"PolyAT",
                0xB0: u"CC",
                0xC0: u"PrgChg",
                0xD0: u"ChanAT",
                0xE0: u"PitchB",
                0xF0: u"Sysex/RT",
            }.get(status_nibble, u"0x{:02X}".format(status_nibble))
            hex_dump = u" ".join(u"{:02X}".format(b) for b in midi_bytes[:8])
            logger.info(
                u"PC12 MIDI RX  ch={:2d}  {:8s}  len={}  bytes=[{}]".format(
                    channel_one_based, kind_label, len(midi_bytes), hex_dump
                )
            )
        super(PC12Surface, self).process_midi_bytes(midi_bytes, midi_processor)

    def disconnect(self):
        for encoder_row_binder in getattr(self, "_all_direct_parameter_encoder_row_binders", []):
            encoder_row_binder.disconnect()
        for button_row_binder in getattr(self, "_all_device_on_off_button_row_binders", []):
            button_row_binder.disconnect()
        track_arm_binder = getattr(self, "_track_arm_button_row_binder", None)
        if track_arm_binder is not None:
            track_arm_binder.disconnect()
        super(PC12Surface, self).disconnect()
