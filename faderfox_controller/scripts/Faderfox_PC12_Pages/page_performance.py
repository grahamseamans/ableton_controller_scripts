from __future__ import absolute_import, print_function, unicode_literals

from .track_device_finder import (
    find_filter_eq_eight_device_on_track,
    find_named_parameter_on_device,
)


# Performance page row E controls the high-pass cutoff on band 1 of the
# filter EQ Eight (the second Eq8 in the chain). Row F controls the low-pass
# cutoff on band 2. The user is responsible for setting band 1 to high-pass
# and band 2 to low-pass on each track's filter EQ Eight.
# TODO verify "1 Frequency A" and "2 Frequency A" parameter names at runtime.

FILTER_EQ_EIGHT_HIGH_PASS_BAND_FREQUENCY_PARAMETER_NAME = u"1 Frequency A"
FILTER_EQ_EIGHT_LOW_PASS_BAND_FREQUENCY_PARAMETER_NAME = u"2 Frequency A"


def find_filter_eq_high_pass_frequency_parameter_for_track(live_track):
    return find_named_parameter_on_device(
        find_filter_eq_eight_device_on_track(live_track),
        FILTER_EQ_EIGHT_HIGH_PASS_BAND_FREQUENCY_PARAMETER_NAME,
    )


def find_filter_eq_low_pass_frequency_parameter_for_track(live_track):
    return find_named_parameter_on_device(
        find_filter_eq_eight_device_on_track(live_track),
        FILTER_EQ_EIGHT_LOW_PASS_BAND_FREQUENCY_PARAMETER_NAME,
    )
