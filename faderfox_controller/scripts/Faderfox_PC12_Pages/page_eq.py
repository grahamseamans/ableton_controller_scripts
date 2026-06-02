from __future__ import absolute_import, print_function, unicode_literals

from .track_device_finder import (
    find_tonal_eq_eight_device_on_track,
    find_named_parameter_on_device,
)


# EQ Eight per-band parameter naming convention used by Live:
#   "<band_index_1_to_8> Frequency A" and "<band_index_1_to_8> Gain A".
# Band 1 = low shelf, band 2 = bell, band 3 = high shelf (user-configured).
# TODO verify exact naming ("1 Frequency A" vs "1 Frequency" etc.) against
# device.parameters[*].name on the user's Live version.

EQ_EIGHT_BAND_1_GAIN_PARAMETER_NAME = u"1 Gain A"
EQ_EIGHT_BAND_1_FREQUENCY_PARAMETER_NAME = u"1 Frequency A"
EQ_EIGHT_BAND_2_GAIN_PARAMETER_NAME = u"2 Gain A"
EQ_EIGHT_BAND_2_FREQUENCY_PARAMETER_NAME = u"2 Frequency A"
EQ_EIGHT_BAND_3_GAIN_PARAMETER_NAME = u"3 Gain A"
EQ_EIGHT_BAND_3_FREQUENCY_PARAMETER_NAME = u"3 Frequency A"


def _find_named_parameter_on_tonal_eq_eight_for_track(live_track, parameter_name):
    return find_named_parameter_on_device(
        find_tonal_eq_eight_device_on_track(live_track), parameter_name
    )


def find_tonal_eq_band_1_gain_parameter_for_track(live_track):
    return _find_named_parameter_on_tonal_eq_eight_for_track(
        live_track, EQ_EIGHT_BAND_1_GAIN_PARAMETER_NAME
    )


def find_tonal_eq_band_1_frequency_parameter_for_track(live_track):
    return _find_named_parameter_on_tonal_eq_eight_for_track(
        live_track, EQ_EIGHT_BAND_1_FREQUENCY_PARAMETER_NAME
    )


def find_tonal_eq_band_2_gain_parameter_for_track(live_track):
    return _find_named_parameter_on_tonal_eq_eight_for_track(
        live_track, EQ_EIGHT_BAND_2_GAIN_PARAMETER_NAME
    )


def find_tonal_eq_band_2_frequency_parameter_for_track(live_track):
    return _find_named_parameter_on_tonal_eq_eight_for_track(
        live_track, EQ_EIGHT_BAND_2_FREQUENCY_PARAMETER_NAME
    )


def find_tonal_eq_band_3_gain_parameter_for_track(live_track):
    return _find_named_parameter_on_tonal_eq_eight_for_track(
        live_track, EQ_EIGHT_BAND_3_GAIN_PARAMETER_NAME
    )


def find_tonal_eq_band_3_frequency_parameter_for_track(live_track):
    return _find_named_parameter_on_tonal_eq_eight_for_track(
        live_track, EQ_EIGHT_BAND_3_FREQUENCY_PARAMETER_NAME
    )


def find_tonal_eq_eight_device_for_track(live_track):
    return find_tonal_eq_eight_device_on_track(live_track)
