from __future__ import absolute_import, print_function, unicode_literals

import Live

from ableton.v2.control_surface import MIDI_CC_TYPE, CompoundElement
from ableton.v2.control_surface.elements import (
    ButtonElement,
    EncoderElement,
    SliderElement,
)

from .mx12_cc_layout import (
    MX12_NUMBER_OF_TRACKS,
    MX12_MIDI_CHANNEL_INDEX_SETUP_1,
    MX12_FADER_CC_BASE,
    MX12_POT_ROW_B_PAN_CC_BASE,
    MX12_GRAY_BUTTON_SOLO_CC_BASE,
    MX12_GREEN_BUTTON_MUTE_CC_BASE,
    MX12_ENCODER_TURN_CC,
    MX12_ENCODER_PUSH_CC,
)


class MX12Elements:
    def __init__(self):
        midi_channel_index = MX12_MIDI_CHANNEL_INDEX_SETUP_1

        track_volume_fader_elements = [
            SliderElement(
                MIDI_CC_TYPE,
                midi_channel_index,
                MX12_FADER_CC_BASE + track_index,
                name=u"MX12_Volume_Fader_{}".format(track_index + 1),
            )
            for track_index in range(MX12_NUMBER_OF_TRACKS)
        ]
        self.track_volume_fader_compound = CompoundElement(
            control_elements=track_volume_fader_elements,
            name=u"MX12_Volume_Fader_Row",
        )

        track_pan_pot_row_b_elements = [
            EncoderElement(
                MIDI_CC_TYPE,
                midi_channel_index,
                MX12_POT_ROW_B_PAN_CC_BASE + track_index,
                Live.MidiMap.MapMode.absolute,
                name=u"MX12_Pan_Pot_Row_B_{}".format(track_index + 1),
            )
            for track_index in range(MX12_NUMBER_OF_TRACKS)
        ]
        self.track_pan_pot_row_b_compound = CompoundElement(
            control_elements=track_pan_pot_row_b_elements,
            name=u"MX12_Pan_Pot_Row_B",
        )

        self.track_solo_gray_button_elements_list = [
            ButtonElement(
                True,
                MIDI_CC_TYPE,
                midi_channel_index,
                MX12_GRAY_BUTTON_SOLO_CC_BASE + track_index,
                name=u"MX12_Solo_Gray_Button_{}".format(track_index + 1),
            )
            for track_index in range(MX12_NUMBER_OF_TRACKS)
        ]

        self.track_mute_green_button_elements_list = [
            ButtonElement(
                True,
                MIDI_CC_TYPE,
                midi_channel_index,
                MX12_GREEN_BUTTON_MUTE_CC_BASE + track_index,
                name=u"MX12_Mute_Green_Button_{}".format(track_index + 1),
            )
            for track_index in range(MX12_NUMBER_OF_TRACKS)
        ]

        self.scene_select_encoder = EncoderElement(
            MIDI_CC_TYPE,
            midi_channel_index,
            MX12_ENCODER_TURN_CC,
            Live.MidiMap.MapMode.absolute,
            name=u"MX12_Scene_Select_Encoder",
        )

        self.scene_launch_push_button = ButtonElement(
            True,
            MIDI_CC_TYPE,
            midi_channel_index,
            MX12_ENCODER_PUSH_CC,
            name=u"MX12_Scene_Launch_Push_Button",
        )
