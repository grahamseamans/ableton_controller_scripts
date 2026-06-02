from __future__ import absolute_import, print_function, unicode_literals
import Live
import logging
from ableton.v2.base import depends, listens
from ableton.v2.control_surface.elements import EncoderElement, SliderElement, MultiElement
from ableton.v2.control_surface import MIDI_CC_TYPE, CompoundElement

from .note_button_element import FaderfoxSysexButtonElement, NoteButtonElement
from .pitch_bend_element import PitchBendElement
from .absolute_encoder_element import AbsoluteEncoderElement
from .consts import *
from .faderfox_display_element import FaderfoxDisplayElement, NUM_DISPLAY_LINE_SEGMENTS
from .faderfox_parameter_display import FaderfoxGlobalDisplay, FaderfoxMessageDisplay, FaderfoxParameterDisplay, FaderfoxTotalDisplay

logger = logging.getLogger(__name__)

device_map = [[(setup, group, index) for setup in DEVICE_DISPLAY_SETUPS for group in [2, 3]] for index in range(NUM_DISPLAY_LINE_SEGMENTS)]

track_map = [[(setup, group, index) for setup in DEVICE_DISPLAY_SETUPS for group in [0, 1, 4, 5, 6, 7]] for index in range(NUM_DISPLAY_LINE_SEGMENTS)]
for setup in [12,13,14,15]:
    for index in range(16):
        track_map[index].append((setup, 8 + index // 4, 12 + index % 4))

senda_map = [[(setup, 8 + index // 4, index % 4) for setup in DEVICE_DISPLAY_SETUPS] for index in range(16)]
sendb_map = [[(setup, 8 + index // 4, 4 + index % 4) for setup in DEVICE_DISPLAY_SETUPS] for index in range(16)]
pan_map = [[(setup, 8 + index // 4, 8 + index % 4) for setup in DEVICE_DISPLAY_SETUPS] for index in range(16)]

@depends(skin=None)
def create_button(channel, identifier, name, **k):
    button = NoteButtonElement(channel, identifier, name=name, **k)
    button.set_feedback_delay(-1)
    return button

class FaderfoxEncoder(EncoderElement):
    @depends(faderfox_settings=None)
    def __init__(self, parameter_display, msg_type, channel, identifier, map_mode, encoder_sensitivity=None, faderfox_settings=None, *a, **k):
        super(FaderfoxEncoder, self).__init__(msg_type, channel, identifier, map_mode, encoder_sensitivity, *a, **k)
        assert faderfox_settings is not None
        self._settings = faderfox_settings
        self._parameter_display = parameter_display
        self.set_needs_takeover(False)
        self.__on_value_changed.subject = self

    @listens(u'value')
    def __on_value_changed(self, _value):
        parameter = self._direct_parameter
        if parameter is not None and self._settings.temp_param_display:
            self._parameter_display.show_parameter(parameter)

    def connect_to_direct(self, parameter):
        self._direct_parameter = parameter

# Live.MidiMap.MapMode.absolute
# Live.MidiMap.MapMode.absolute_14_bit
# Live.MidiMap.MapMode.relative_signed_bit
# Live.MidiMap.MapMode.relative_smooth_signed_bit
# Live.MidiMap.MapMode.relative_signed_bit2
# Live.MidiMap.MapMode.relative_smooth_signed_bit2
# Live.MidiMap.MapMode.relative_binary_offset
# Live.MidiMap.MapMode.relative_smooth_binary_offset
# Live.MidiMap.MapMode.relative_two_compliment
# Live.MidiMap.MapMode.relative_smooth_two_compliment

def create_macro_encoder(parameter_display, channel, identifier, name, map_mode=Live.MidiMap.MapMode.absolute):
    encoder = FaderfoxEncoder(parameter_display, MIDI_CC_TYPE, channel, identifier, map_mode, name=name)
    return encoder

def create_encoder(channel, identifier, name, map_mode=Live.MidiMap.MapMode.absolute):
    Element = AbsoluteEncoderElement if map_mode == Live.MidiMap.MapMode.absolute else EncoderElement
    encoder = Element(MIDI_CC_TYPE, channel, identifier, map_mode, name=name)
    if map_mode != Live.MidiMap.MapMode.absolute:
        encoder.set_feedback_delay(-1)
    return encoder

def create_slider(channel, identifier, name):
    slider = SliderElement(MIDI_CC_TYPE, channel, identifier, name=name)
    return slider

def numbers(base):
    return ((index, FaderfoxUniversal_CH1 + (index // 8), base + (index % 8)) for index in range(NUMBER_TRACKS))

def button_base(base, name):
    return CompoundElement(
        control_elements=[
            create_button(channel, identifier, name + u'_{}'.format(index))
            for (index, channel, identifier) in numbers(base)
        ],
        name=name + u'_Buttons',
    )


def encoder_base(base, name):
    return CompoundElement(
        control_elements=[
            create_encoder(channel, identifier, name + u'_{}'.format(index))
            for (index, channel, identifier) in numbers(base)
        ],
        name=name + u'_Encoders',
    )


def slider_base(base, name):
    return CompoundElement(
        control_elements=[
            create_slider(channel, identifier,
                          name=name + u'_{}'.format(index))
            for (index, channel, identifier) in numbers(base)
        ],
        name=name + u'_Sliders',
    )


def send_element_row(index, channel, identifier):
    return CompoundElement(
        control_elements=[
            create_encoder(channel, CC_TRACK_SEND1_BASE +
                           identifier, u'Send1_Encoder_{}'.format(index)),
            create_encoder(channel, CC_TRACK_SEND2_BASE +
                           identifier, u'Send2_Encoder_{}'.format(index)),
            create_encoder(channel, CC_TRACK_SEND3_BASE +
                           identifier, u'Send3_Encoder_{}'.format(index)),
            create_encoder(channel, CC_TRACK_SEND4_BASE +
                           identifier, u'Send4_Encoder_{}'.format(index)),
        ],
        name=u'Send_Encoders_{}'.format(index),
    )


class MultiEncoderElement(CompoundElement):
    def send_value(self, value):
        for control in self.owned_control_elements():
            control.send_value(value)

    def normalize_value(self, value):
        return self.owned_control_elements()[0].normalize_value(value)


class FaderfoxElements:
    def __init__(self):
        self.track_select_buttons = button_base(
            NOTE_SELECT_TRACK_BASE, u'Track_Select')
        self.mute_buttons = button_base(NOTE_MUTE_TRACK_BASE, u'Mute')
        self.arm_buttons = button_base(NOTE_ARM_TRACK_BASE, u'Arm')
        self.monitor_buttons = button_base(NOTE_MONITOR_TRACK_BASE, u'Monitor')
        self.solo_buttons = button_base(NOTE_SOLO_TRACK_BASE, u'Solo')

        self.volume_encoders = slider_base(CC_TRACK_VOLUME_BASE, u'Volume')
        self.pan_encoders = encoder_base(CC_TRACK_PAN_BASE, u'Pan')
        self.send_encoders = CompoundElement(
            control_elements=[send_element_row(index, channel, identifier) for (
                index, channel, identifier) in numbers(0)],
            name=u'Send_Encoders'
        )

        self.display_parameters = FaderfoxParameterDisplay()
        self.display_global = FaderfoxGlobalDisplay()
        self.display_message = FaderfoxMessageDisplay()

        self.display_total = FaderfoxTotalDisplay(layers = [self.display_parameters, self.display_global, self.display_message])

        self._parameter_display_buttons_raw = [
            create_button(FaderfoxUniversal_CH1, NOTE_PARAMETER_DISPLAY_BASE + index, u'Parameter_Display_Button_{}'.format(index))
            for index in range(16)
        ]

        self.parameter_display_buttons = CompoundElement(
            control_elements=self._parameter_display_buttons_raw, name=u'Parameter_Display_Buttons'
        )

        self._macro_encoders_raw = [
            create_macro_encoder(self.display_parameters, FaderfoxUniversal_CH1 if index < 8 else FaderfoxUniversal_CH2,
                (CC_MACRO_BASE_SELECTED_TRACK + index) if index < 8 else (CC_MACRO_HIGH_BASE_SELECTED_TRACK + index - 8),
                u'Macro_{}'.format(index + 1)
            ) for index in range(16)
        ]

        self.macro_encoders = CompoundElement(
            control_elements=self._macro_encoders_raw, name=u'Macro_Encoders'
        )

        self.selected_send_encoders = CompoundElement(
            control_elements=[
                create_encoder(
                    FaderfoxUniversal_CH2,
                    CC_SEND_SELECTED_TRACK_BASE +
                    index if index < 3 else CC_HIGH_SEND_SELECTED_TRACK_BASE + index - 3,
                    u'Selected_Send_{}'.format(index),
                )
                for index in range(12)
            ],
            name=u'Selected_Send_Encoders',
        )

        self.selected_pan_encoder = create_encoder(
            FaderfoxUniversal_CH2, CC_PAN_SELECTED_TRACK, u'Selected_Pan'
        )
        self.selected_volume_encoder = create_encoder(
            FaderfoxUniversal_CH2, CC_VOLUME_SELECTED_TRACK, u'Selected_Volume'
        )

        self.selected_arm_button = create_button(
            FaderfoxUniversal_CH2, NOTE_ARM_SELECTED, u'Selected_Arm'
        )
        self.selected_monitor_button = create_button(
            FaderfoxUniversal_CH2, NOTE_MONITOR_SELECTED, u'Selected_Monitor'
        )
        self.selected_solo_button = create_button(
            FaderfoxUniversal_CH2, NOTE_SOLO_SELECTED, u'Selected_Solo'
        )
        self.selected_mute_button = create_button(
            FaderfoxUniversal_CH2, NOTE_MUTE_SELECTED, u'Selected_Mute'
        )

        self.scene_select_encoder = MultiEncoderElement(control_elements=[
            create_encoder(FaderfoxUniversal_CH1, CC_SCENE_SELECT, u'Select_Scene_CH1',
                           Live.MidiMap.MapMode.relative_smooth_two_compliment),
            create_encoder(FaderfoxUniversal_CH2, CC_SCENE_SELECT, u'Select_Scene_CH2',
                           Live.MidiMap.MapMode.relative_smooth_two_compliment)
        ], name=u'Select_Scene')

        self.track_select_encoder = MultiEncoderElement(control_elements=[
            create_encoder(FaderfoxUniversal_CH1, CC_TRACK_SELECT, u'Select_Track_CH1',
                           Live.MidiMap.MapMode.relative_smooth_two_compliment),
            create_encoder(FaderfoxUniversal_CH2, CC_TRACK_SELECT, u'Select_Track_CH2',
                           Live.MidiMap.MapMode.relative_smooth_two_compliment),
        ], name=u'Select_Track')

        self.track_view_button = create_button(
            FaderfoxUniversal_CH2, NOTE_TRACK_VIEW, u'Track_View')
        self.clip_view_button = create_button(
            FaderfoxUniversal_CH2, NOTE_CLIP_VIEW, u'Clip_View')

        self.launch_clip_button = create_button(
            FaderfoxUniversal_CH2, NOTE_LAUNCH_CLIP_SELECTED, u'Launch_Clip')
        self.stop_track_button = create_button(
            FaderfoxUniversal_CH2, NOTE_STOP_CLIP_SELECTED, u'Stop_Track')

        self.launch_clip_buttons = button_base(
            NOTE_LAUNCH_TRACK_BASE, u'Launch_Clip')
        self.stop_track_buttons = button_base(
            NOTE_STOP_TRACK_BASE, u'Stop_Track')

        self.tempo_coarse_encoder = create_encoder(
            FaderfoxUniversal_CH1,
            CC_TEMPO_COARSE,
            u'Tempo_Coarse',
            Live.MidiMap.MapMode.relative_smooth_two_compliment,
        )
        self.tempo_fine_encoder = create_encoder(
            FaderfoxUniversal_CH1,
            CC_TEMPO_FINE,
            u'Tempo_Fine',
            Live.MidiMap.MapMode.relative_smooth_two_compliment,
        )

        self.play_button = create_button(
            FaderfoxUniversal_CH1, NOTE_GLOBAL_PLAY, u'Global_Play')
        self.stop_button = create_button(
            FaderfoxUniversal_CH1, NOTE_GLOBAL_STOP, u'Global_Stop')
        self.record_button = create_button(
            FaderfoxUniversal_CH1, NOTE_GLOBAL_RECORD, u'Global_Record')

        self.nudge_up_button = create_button(
            FaderfoxUniversal_CH1, NOTE_NUDGE_UP, u'Nudge_Up')
        self.nudge_down_button = create_button(
            FaderfoxUniversal_CH1, NOTE_NUDGE_DOWN, u'Nudge_Down')

        self.master_pan_encoder = create_encoder(
            FaderfoxUniversal_CH1, CC_MASTER_PAN, u'Master_Pan')
        self.master_volume_encoder = create_encoder(
            FaderfoxUniversal_CH1, CC_MASTER_VOLUME, u'Master_Volume')
        self.cue_volume_encoder = create_encoder(
            FaderfoxUniversal_CH1, CC_CUE_VOLUME, u'Cue_Volume')

        self.arranger_view_button = create_button(
            FaderfoxUniversal_CH1, NOTE_SWITCH_ARRANGEMENT_VIEW, u'Arranger_View')
        self.launch_selected_scene_button = create_button(
            FaderfoxUniversal_CH1, NOTE_START_SCENE, u'Launch_Selected_Scene')
        self.stop_selected_scene_button = create_button(
            FaderfoxUniversal_CH1, NOTE_STOP_SCENE, u'Stop_Selected_Scene')

        self.quantization_encoder = create_encoder(
            FaderfoxUniversal_CH1, CC_QUANTIZATION, u'Clip_Quantization')

        self.pitch_bend = PitchBendElement(FaderfoxUniversal_CH1)

        self.crossfader = create_slider(
            FaderfoxUniversal_CH2, CC_CROSSFADE, u'Crossfader')

        self.crossfader_assign = AbsoluteEncoderElement(
            MIDI_CC_TYPE, FaderfoxUniversal_CH2, CC_CROSSFADER_ASSIGN, Live.MidiMap.MapMode.absolute, name=u'Crossfader_Assign')

        self.faderfox_display = FaderfoxDisplayElement(name=u'Faderfox_Display', enabled=False)

        self.device_display = self.faderfox_display.add_part(device_map)
        self.track_display = self.faderfox_display.add_part(track_map)
        self.send_a_display = self.faderfox_display.add_part(senda_map)
        self.send_b_display = self.faderfox_display.add_part(sendb_map)
        self.pan_display = self.faderfox_display.add_part(pan_map)

        self.sx_buttons_raw = [
            FaderfoxSysexButtonElement(sysex_identifier=EC4_SYSEX_BUTTON_IDENTIFIER + get_ec4_bp_sysex_button(index), name=u'SX-PB{}'.format(index))
            for index in range(16)
        ]

        self.sx_user_buttons_raw = [
            FaderfoxSysexButtonElement(sysex_identifier=EC4_SYSEX_BUTTON_IDENTIFIER + EC4_SYSEX_USER_BUTTONS[index], name=u'SX-USER{}'.format(index))
            for index in range(4)
        ]

        self.user1_button = self.sx_user_buttons_raw[0]
        self.user2_button = self.sx_user_buttons_raw[1]
        self.user3_button = self.sx_user_buttons_raw[2]
        self.user4_button = self.sx_user_buttons_raw[3]

        self.rack_show_hide_button = MultiElement(
            create_button(FaderfoxUniversal_CH1, NOTE_RACK_TRACK_VIEW, u'Rack_Show_Hide'),
            self.sx_buttons_raw[15]
        )
        self.device_on_off_button = MultiElement(
            create_button(FaderfoxUniversal_CH1, NOTE_RACK_ON_OFF, u'Device_On_Off'),
            self.sx_buttons_raw[12]
        )

        self.device_first_button = self.sx_buttons_raw[4]
        self.device_prev_button = MultiElement(
            create_button(FaderfoxUniversal_CH1, NOTE_PREVIOUS_RACK, u'Device_Prev'),
            self.sx_buttons_raw[5]
        )
        self.device_next_button = MultiElement(
            create_button(FaderfoxUniversal_CH1, NOTE_NEXT_RACK, u'Device_Next'),
            self.sx_buttons_raw[6]
        )
        self.device_last_button = self.sx_buttons_raw[7]

        self.device_show_hide_button = MultiElement(
            create_button(FaderfoxUniversal_CH1, NOTE_SHOW_RACK, u'Device_Show_Hide'),
            self.sx_buttons_raw[14]
        )
        self.device_lock_button = MultiElement(
            create_button(FaderfoxUniversal_CH1, NOTE_LOCK_RACK, u'Device_Lock'),
            self.sx_buttons_raw[13]
        )

        self.first_track_button = self.sx_buttons_raw[0]
        self.prev_track_button = MultiElement(
            create_button(FaderfoxUniversal_CH1, NOTE_PREVIOUS_TRACK, u'Track_Prev'),
            self.sx_buttons_raw[1]
        )
        self.next_track_button = MultiElement(
            create_button(FaderfoxUniversal_CH1, NOTE_NEXT_TRACK, u'Track_Next'),
            self.sx_buttons_raw[2]
        )
        self.last_track_button = self.sx_buttons_raw[3]

        self.first_device_bank_button = self.sx_buttons_raw[8]
        self.prev_device_bank_button = MultiElement(
            create_button(FaderfoxUniversal_CH2, NOTE_PREVIOUS_BANK, u'Prev_Device_Bank'),
            self.sx_buttons_raw[9]
        )
        self.next_device_bank_button = MultiElement(
            create_button(FaderfoxUniversal_CH2, NOTE_NEXT_BANK, u'Next_Device_Bank'),
            self.sx_buttons_raw[10]
        )
        self.last_device_bank_button = self.sx_buttons_raw[11]

        self.shift_button = FaderfoxSysexButtonElement(sysex_identifier=EC4_SYSEX_BUTTON_IDENTIFIER + EC4_SYSEX_SHIFT_BUTTON, name=u'Shift_Button')
#
    def set_group(self, group):
        self.faderfox_display.set_group(group)
