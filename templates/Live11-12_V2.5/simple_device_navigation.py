from __future__ import absolute_import, print_function, unicode_literals
from Faderfox_Universal_2.consts import NavPosition
import Live
import logging
from ableton.v2.control_surface import Component
from ableton.v2.control_surface.control import ButtonControl
NavDirection = Live.Application.Application.View.NavDirection

logger = logging.getLogger(__name__)

class SimpleDeviceNavigationComponent(Component):
    u"""
    Device navigation component for the case where
    we only need to go to the next or previous device
    on a track.
    """
    next_button = ButtonControl()
    prev_button = ButtonControl()
    first_button = ButtonControl()
    last_button = ButtonControl()

    @first_button.pressed
    def _first_button(self, value):
        #logger.info(u'next_button pressed')
        self._scroll_device_chain(NavPosition.First)

    @prev_button.pressed
    def _prev_button(self, value):
        #logger.info(u'prev_button pressed')
        self._scroll_device_chain(NavPosition.Prev)

    @next_button.pressed
    def _next_button(self, value):
        #logger.info(u'next_button pressed')
        self._scroll_device_chain(NavPosition.Next)

    @last_button.pressed
    def _last_button(self, value):
        #logger.info(u'next_button pressed')
        self._scroll_device_chain(NavPosition.Last)

    def _append_devices(self, devices, device):
        devices.append(device)
        if device.can_have_chains and hasattr(device.view, "is_showing_chain_devices") and device.view.is_showing_chain_devices:
            for device in device.view.selected_chain.devices:
                self._append_devices(devices, device)

    def _get_devices(self):
        selected_track = self.song.view.selected_track
        if not selected_track:
            return []
        devices = []
        for device in selected_track.devices:
            self._append_devices(devices, device)
        return devices

    def _scroll_device_chain(self, nav_position):
        devices = self._get_devices()

        selected_track = self.song.view.selected_track
        if not selected_track:
            return

        selected_device = selected_track.view.selected_device

        index = 0
        if selected_device in devices:
            index = list(devices).index(selected_device)

        if nav_position == NavPosition.First:
            index = 0
        elif nav_position == NavPosition.Last:
            index = len(devices) - 1
        elif nav_position == NavPosition.Next:
            index = index + 1
        elif nav_position == NavPosition.Prev:
            index = index - 1

        index = max(0, min(index, len(devices)-1))

        self.song.view.select_device(devices[index])
