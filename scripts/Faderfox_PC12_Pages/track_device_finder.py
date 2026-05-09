from __future__ import absolute_import, print_function, unicode_literals


# Live's internal device class names used to identify per-track devices:
#   "Eq8"         -> EQ Eight
#   "Compressor2" -> Compressor (legacy "2" suffix preserved by Live for many releases)
# TODO verify both class_name strings against track.devices[*].class_name in
# Live's Python console on the user's running version (12.x at time of writing).

EQ_EIGHT_CLASS_NAME = u"Eq8"
COMPRESSOR_CLASS_NAME = u"Compressor2"


def find_tonal_eq_eight_device_on_track(live_track):
    eq_eight_devices_on_track_in_chain_order = [
        device for device in live_track.devices if device.class_name == EQ_EIGHT_CLASS_NAME
    ]
    if len(eq_eight_devices_on_track_in_chain_order) < 1:
        return None
    return eq_eight_devices_on_track_in_chain_order[0]


def find_filter_eq_eight_device_on_track(live_track):
    eq_eight_devices_on_track_in_chain_order = [
        device for device in live_track.devices if device.class_name == EQ_EIGHT_CLASS_NAME
    ]
    if len(eq_eight_devices_on_track_in_chain_order) < 2:
        return None
    return eq_eight_devices_on_track_in_chain_order[1]


def find_compressor_device_on_track(live_track):
    compressor_devices_on_track_in_chain_order = [
        device for device in live_track.devices if device.class_name == COMPRESSOR_CLASS_NAME
    ]
    if len(compressor_devices_on_track_in_chain_order) < 1:
        return None
    return compressor_devices_on_track_in_chain_order[0]


def find_named_parameter_on_device(live_device, parameter_name):
    if live_device is None:
        return None
    for device_parameter in live_device.parameters:
        if device_parameter.name == parameter_name:
            return device_parameter
    return None
