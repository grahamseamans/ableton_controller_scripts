from __future__ import absolute_import, print_function, unicode_literals

from Faderfox_Universal_2.faderfox_settings import FaderfoxEc4SettingComponent, FaderfoxEc4Settings

from .consts import *
from .skin_default import default_skin
from .FaderfoxElements import FaderfoxElements
from .transport_component import TransportComponent
from .view_control_component import ViewControlComponent
from .mixer_component import MixerComponent
from .device_component import DeviceComponent
import logging
from ableton.v2.base.collection import IndexedDict
from ableton.v2.base import inject, const, task
from ableton.v2.control_surface import (
    ControlSurface,
    DeviceDecoratorFactory,
    Layer,
    BankingInfo,
    BANK_PARAMETERS_KEY,
)
from ableton.v2.control_surface.components import (
    SessionRingComponent,
    SimpleTrackAssigner,
)
from ableton.v2.control_surface.default_bank_definitions import BANK_DEFINITIONS
from .device_parameter_component import DisplayingDeviceParameterComponent
from .simple_device_navigation import SimpleDeviceNavigationComponent
from math import ceil

logger = logging.getLogger(__name__)

MY_DEFINITIONS = IndexedDict()
SYSEX_REQUEST_SETUP_REQUEST = (0xf0, 0x00, 0x00, 0x00, 0x4e, 0x20, 0x10, 0xf7)

for key, definition in BANK_DEFINITIONS.items():
    count = len(definition)
    newdict = IndexedDict()
    for i in range(ceil(count / 2)):
        n = i * 2
        l = definition.value_by_index(n)[BANK_PARAMETERS_KEY]
        if n < count-1:
            l += definition.value_by_index(n + 1)[BANK_PARAMETERS_KEY]
        newdict[definition.key_by_index(n)] = {BANK_PARAMETERS_KEY: l}
    MY_DEFINITIONS[key] = newdict

class FaderfoxSurface(ControlSurface):
    __doc__ = u'Faderfox Universal controller script'
    __version__ = u'v2.5'
    __name__ = u'Faderfox Universal'
    __module__ = __name__

    _current_group = None
    _faderfox_device = None

    def __init__(self, *a, **k):
        super(FaderfoxSurface, self).__init__(*a, **k)

        self._faderfox_settings = FaderfoxEc4Settings()

        self._create_elements()
        self._create_components()

        self.show_message(u'{} {}'.format(self.__name__, self.__version__))

    def port_settings_changed(self):
        super(FaderfoxSurface, self).port_settings_changed()
        self._elements.display_message.show_message("Connected to Live", self.__name__, self.__version__)
        self._get_setup_request_task = self._tasks.add(task.run(self._send_get_setup_request))

    def _send_get_setup_request(self):
        #logger.info(u'Sending setup request')
        self._send_midi(SYSEX_REQUEST_SETUP_REQUEST)

    def process_midi_bytes(self, midi_bytes, midi_processor):
        #logger.info(u'MIDI bytes: {}'.format(midi_bytes))
        self._get_faderfox_device(midi_bytes)

        if self._is_ec4_sysex_response(midi_bytes):
            if self._is_ec4_sysex_setup_response(midi_bytes):
                setup = midi_bytes[9] & 0x0F
                group = midi_bytes[12] & 0x0F
                self._set_current_group(setup, group)
                return
            elif len(midi_bytes) == 8:
                return

        super(FaderfoxSurface, self).process_midi_bytes(midi_bytes, midi_processor)

    def _set_current_group(self, setup, group):
        self._current_group = (setup, group)
        self._elements.set_group(self._current_group)
        self._faderfox_settings.setup = setup
        self._faderfox_settings.group = group
        self._faderfox_settings.is_device_group = setup in DEVICE_DISPLAY_SETUPS and group in DEVICE_DISPLAY_GROUPS
        #logger.info(u'Group change: {}'.format(self._current_group))
        return

    def update_display_hook(self):
        self._elements.display_total.update_display()

    def _get_faderfox_device(self, midi_bytes):
        if self._faderfox_device is None and (len(midi_bytes) >= 8 and midi_bytes[0:6] == (0xf0, 0x00, 0x00, 0x00, 0x4e, 0x2c)):
            device = midi_bytes[6] - 0x10
            if FADERFOX_DEVICE_NAMES.get(device) is not None:
                self._faderfox_device = device
                if device == FADERFOX_DEVICE_EC4:
                    self._elements.faderfox_display.set_enabled(True)
            msg = u'Connected to Faderfox {}'.format(FADERFOX_DEVICE_NAMES.get(device) or u'Unknown (0x{:02x})'.format(device))
            logger.info(msg)
            #self.show_message(msg)

    def _is_ec4_sysex_setup_response(self, midi_bytes):
        return self._is_ec4_sysex_response(midi_bytes) and len(midi_bytes) == 14 and midi_bytes[7:9] == (0x4e, 0x28) and midi_bytes[10:12] == (0x4e, 0x24) and midi_bytes[13] == 0xf7

    def _is_ec4_sysex_response(self, midi_bytes):
        return len(midi_bytes) >= 8 and midi_bytes[:7] == (0xf0, 0x00, 0x00, 0x00, 0x4e, 0x2c, 0x1b)

    def _create_elements(self):
        with self.component_guard():
            with inject(skin=const(default_skin),faderfox_settings=const(self._faderfox_settings)).everywhere():
                self._elements = FaderfoxElements()

    def _create_components(self):
        with self.component_guard():
            with inject(element_container=const(self._elements),faderfox_settings=const(self._faderfox_settings)).everywhere():
                self._create_mixer()
                self._create_view_control()
                self._create_transport()
                self._create_device()
                self._create_settings()

    def _create_settings(self):
        self._settings_control = FaderfoxEc4SettingComponent(is_enabled=False, name=u'Faderfox_Settings',
            show_message=self.show_message,
            layer = Layer(
                temp_param_display_button=u'user1_button',
                perm_param_display_button=u'user2_button',
                set_defaults_button=u'user3_button',
                global_display_button=u'user4_button',

                #message_display=u'display_message',
            ))

        self._settings_control.set_enabled(True)

    def _create_mixer(self):
        self._session_ring = SessionRingComponent(
            is_enabled=False,
            num_tracks=NUMBER_TRACKS,
            tracks_to_use=lambda: tuple(
                self.song.tracks) + tuple(self.song.return_tracks) + (self.song.master_track,),
            name=u'Session_Ring',
        )

        mixerLayer = Layer(
            arm_buttons=u'arm_buttons',
            monitor_buttons=u'monitor_buttons',
            solo_buttons=u'solo_buttons',
            mute_buttons=u'mute_buttons',
            launch_clip_buttons=u'launch_clip_buttons',
            stop_buttons=u'stop_track_buttons',

            track_select_buttons=u'track_select_buttons',
            volume_controls=u'volume_encoders',
            pan_controls=u'pan_encoders',
            send_controls=u'send_encoders',
            prehear_volume_control=u'cue_volume_encoder',

            crossfader_control=u'crossfader',
            track_display=u'track_display',
            send_a_display=u'send_a_display',
            send_b_display=u'send_b_display',
            pan_display=u'pan_display',

            global_display=u'display_global',
        )

        self._mixer = MixerComponent(
            is_enabled=False,
            tracks_provider=self._session_ring,
            track_assigner=SimpleTrackAssigner(),
            name=u'Mixer',
            layer=mixerLayer,
        )

        self._mixer.selected_strip().layer = Layer(
            arm_button=u'selected_arm_button',
            monitor_button=u'selected_monitor_button',
            solo_button=u'selected_solo_button',
            mute_button=u'selected_mute_button',
            launch_clip_button=u'launch_clip_button',
            stop_button=u'stop_track_button',

            volume_control=u'selected_volume_encoder',
            pan_control=u'selected_pan_encoder',
            send_controls=u'selected_send_encoders',
            crossfade_toggle=u'crossfader_assign',
        )

        self._mixer.master_strip().layer = Layer(
            volume_control=u'master_volume_encoder',
            pan_control=u'master_pan_encoder',
        )

        # self._session_ring.set_enabled(True)
        self._mixer.set_enabled(True)

    def _create_view_control(self):
        viewLayer = Layer(
            track_view_button=u'track_view_button',
            clip_view_button=u'clip_view_button',
            scene_select_encoder=u'scene_select_encoder',
            track_select_encoder=u'track_select_encoder',
            arranger_view_button=u'arranger_view_button',
            first_track_button=u'first_track_button',
            prev_track_button=u'prev_track_button',
            next_track_button=u'next_track_button',
            last_track_button=u'last_track_button',
        )
        self._view_control = ViewControlComponent(
            is_enabled=False, name=u'View_Control', layer=viewLayer, session_ring=self._session_ring)
        self._view_control.set_enabled(True)

    def _create_device(self):
        self._banking_info = BankingInfo(MY_DEFINITIONS)
        self._device = DeviceComponent(
            is_enabled=False,
            device_decorator_factory=DeviceDecoratorFactory(),
            device_bank_registry=self._device_bank_registry,
            banking_info=self._banking_info,
            name=u'Device',
            layer=Layer(
                first_bank_button=u'first_device_bank_button',
                prev_bank_button=u'prev_device_bank_button',
                next_bank_button=u'next_device_bank_button',
                last_bank_button=u'last_device_bank_button',
                global_display=u'display_global',
            )
        )
        self._device_parameters = DisplayingDeviceParameterComponent(
            is_enabled=False,
            parameter_provider=self._device,
            name=u'Device_Parameters',
            toggle_lock=self.toggle_lock,
            layer=Layer(
                parameter_controls=u'macro_encoders',
                name_display_line=u'device_display',
                device_parameter_display=u'display_parameters',

                global_display=u'display_global',
                show_global_display_button=u'shift_button',

                message_display=u'display_message',

                rack_show_hide_button=u'rack_show_hide_button',
                device_on_off_button=u'device_on_off_button',

                device_show_hide_button=u'device_show_hide_button',
                device_lock_button=u'device_lock_button',

                show_parameter_controls=u'parameter_display_buttons',
            )
        )

        self._device_navigation = SimpleDeviceNavigationComponent(
            is_enabled=False,
            name=u'Device_Navigation',
            layer=Layer(
                first_button=u'device_first_button',
                prev_button=u'device_prev_button',
                next_button=u'device_next_button',
                last_button=u'device_last_button',
            ),
        )

        self._device_parameters.set_enabled(True)
        self._device_navigation.set_enabled(True)
        self._device.set_enabled(True)

    def _create_transport(self):
        transportLayer = Layer(
            tempo_control=u'tempo_coarse_encoder',
            tempo_fine_control=u'tempo_fine_encoder',
            tempo_display_control=u'pitch_bend',
            play_button=u'play_button',
            stop_button=u'stop_button',
            record_button=u'record_button',
            nudge_up_button=u'nudge_up_button',
            nudge_down_button=u'nudge_down_button',
            launch_selected_scene_button=u'launch_selected_scene_button',
            stop_selected_scene_button=u'stop_selected_scene_button',
            quantization_control=u'quantization_encoder',
        )
        self._transport = TransportComponent(
            is_enabled=False, name=u'Transport', layer=transportLayer)
        self._transport.set_enabled(True)
