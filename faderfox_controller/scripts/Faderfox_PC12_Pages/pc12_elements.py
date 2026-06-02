from __future__ import absolute_import, print_function, unicode_literals

import Live

from ableton.v2.control_surface import MIDI_CC_TYPE, CompoundElement
from ableton.v2.control_surface.elements import ButtonElement, EncoderElement

from .pc12_cc_layout import (
    PC12_NUMBER_OF_TRACKS,
    PC12_MIDI_CHANNEL_INDEX_PERFORMANCE_PAGE,
    PC12_POT_ROW_A_CC_BASE,
    PC12_POT_ROW_B_CC_BASE,
    PC12_POT_ROW_C_CC_BASE,
    PC12_POT_ROW_D_CC_BASE,
    PC12_GREEN_BUTTON_CC_BASE,
)


class PC12PerformancePageMixerElements:
    def __init__(self):
        midi_channel_index = PC12_MIDI_CHANNEL_INDEX_PERFORMANCE_PAGE

        per_track_send_compound_elements = []
        for track_index in range(PC12_NUMBER_OF_TRACKS):
            send_1_encoder = EncoderElement(
                MIDI_CC_TYPE,
                midi_channel_index,
                PC12_POT_ROW_A_CC_BASE + track_index,
                Live.MidiMap.MapMode.absolute,
                name=u"PC12_Perf_Track{}_Send1".format(track_index + 1),
            )
            send_2_encoder = EncoderElement(
                MIDI_CC_TYPE,
                midi_channel_index,
                PC12_POT_ROW_B_CC_BASE + track_index,
                Live.MidiMap.MapMode.absolute,
                name=u"PC12_Perf_Track{}_Send2".format(track_index + 1),
            )
            send_3_encoder = EncoderElement(
                MIDI_CC_TYPE,
                midi_channel_index,
                PC12_POT_ROW_C_CC_BASE + track_index,
                Live.MidiMap.MapMode.absolute,
                name=u"PC12_Perf_Track{}_Send3".format(track_index + 1),
            )
            send_4_encoder = EncoderElement(
                MIDI_CC_TYPE,
                midi_channel_index,
                PC12_POT_ROW_D_CC_BASE + track_index,
                Live.MidiMap.MapMode.absolute,
                name=u"PC12_Perf_Track{}_Send4".format(track_index + 1),
            )
            per_track_send_compound_elements.append(
                CompoundElement(
                    control_elements=[
                        send_1_encoder,
                        send_2_encoder,
                        send_3_encoder,
                        send_4_encoder,
                    ],
                    name=u"PC12_Perf_Track{}_Sends".format(track_index + 1),
                )
            )

        self.performance_send_encoders_per_track = CompoundElement(
            control_elements=per_track_send_compound_elements,
            name=u"PC12_Perf_Send_Encoders",
        )

        track_arm_button_elements = [
            ButtonElement(
                True,
                MIDI_CC_TYPE,
                midi_channel_index,
                PC12_GREEN_BUTTON_CC_BASE + track_index,
                name=u"PC12_Perf_Arm_Button_{}".format(track_index + 1),
            )
            for track_index in range(PC12_NUMBER_OF_TRACKS)
        ]
        self.performance_arm_button_compound = CompoundElement(
            control_elements=track_arm_button_elements,
            name=u"PC12_Perf_Arm_Button_Row",
        )
