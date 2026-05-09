from __future__ import absolute_import, print_function, unicode_literals

from .track_device_finder import (
    find_compressor_device_on_track,
    find_named_parameter_on_device,
)


COMPRESSOR_THRESHOLD_PARAMETER_NAME = u"Threshold"
COMPRESSOR_RATIO_PARAMETER_NAME = u"Ratio"
COMPRESSOR_ATTACK_PARAMETER_NAME = u"Attack"
COMPRESSOR_RELEASE_PARAMETER_NAME = u"Release"
COMPRESSOR_KNEE_PARAMETER_NAME = u"Knee"
COMPRESSOR_OUTPUT_GAIN_PARAMETER_NAME = u"Output Gain"
# TODO verify the exact Compressor2 parameter names ("Threshold", "Ratio",
# "Attack", "Release", "Knee", "Output Gain") against
# device.parameters[*].name on the user's Live version.


def find_compressor_threshold_parameter_for_track(live_track):
    return find_named_parameter_on_device(
        find_compressor_device_on_track(live_track), COMPRESSOR_THRESHOLD_PARAMETER_NAME
    )


def find_compressor_ratio_parameter_for_track(live_track):
    return find_named_parameter_on_device(
        find_compressor_device_on_track(live_track), COMPRESSOR_RATIO_PARAMETER_NAME
    )


def find_compressor_attack_parameter_for_track(live_track):
    return find_named_parameter_on_device(
        find_compressor_device_on_track(live_track), COMPRESSOR_ATTACK_PARAMETER_NAME
    )


def find_compressor_release_parameter_for_track(live_track):
    return find_named_parameter_on_device(
        find_compressor_device_on_track(live_track), COMPRESSOR_RELEASE_PARAMETER_NAME
    )


def find_compressor_knee_parameter_for_track(live_track):
    return find_named_parameter_on_device(
        find_compressor_device_on_track(live_track), COMPRESSOR_KNEE_PARAMETER_NAME
    )


def find_compressor_output_gain_parameter_for_track(live_track):
    return find_named_parameter_on_device(
        find_compressor_device_on_track(live_track), COMPRESSOR_OUTPUT_GAIN_PARAMETER_NAME
    )


def find_compressor_device_for_track(live_track):
    return find_compressor_device_on_track(live_track)
