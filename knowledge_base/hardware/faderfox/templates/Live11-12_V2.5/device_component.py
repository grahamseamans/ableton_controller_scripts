from __future__ import absolute_import, print_function, unicode_literals
import logging
from Faderfox_Universal_2.consts import NavPosition
from ableton.v2.base import clamp, listens, liveobj_valid
from ableton.v2.control_surface import ParameterInfo, DescribedDeviceParameterBank
from ableton.v2.control_surface.components import DeviceComponent as DeviceComponentBase
from ableton.v2.control_surface.control import ButtonControl
from .device_parameter_bank import create_device_bank

logger = logging.getLogger(__name__)

# def create_device_bank16(device, banking_info):
#     if liveobj_valid(device) and banking_info.device_bank_definition(device) is not None:
#         return DescribedDeviceParameterBank(device=device, size=16, banking_info=banking_info)

#     return create_device_bank(device, banking_info)

class DeviceComponent(DeviceComponentBase):
    first_bank_button = ButtonControl()
    prev_bank_button = ButtonControl()
    next_bank_button = ButtonControl()
    last_bank_button = ButtonControl()

    _global_display = None

    def _create_parameter_info(self, parameter, name):
        return ParameterInfo(
            parameter=parameter, name=name, default_encoder_sensitivity=1.0
        )

    def _setup_bank(self, device, bank_factory=create_device_bank):
        super(DeviceComponent, self)._setup_bank(device, bank_factory)

    def set_global_display(self, display):
        self._global_display = display
        self._update_global_display()

    @first_bank_button.pressed
    def _first_bank_button(self, _):
        self._scroll_bank(NavPosition.First)

    @prev_bank_button.pressed
    def _prev_bank_button(self, _):
        self._scroll_bank(NavPosition.Prev)

    @next_bank_button.pressed
    def _next_bank_button(self, _):
        self._scroll_bank(NavPosition.Next)

    @last_bank_button.pressed
    def _last_bank_button(self, _):
        self._scroll_bank(NavPosition.Last)

    def _set_bank_index(self, bank):
        super()._set_bank_index(bank)
        self._update_global_display()

    def _update_global_display(self):
        bank = self._bank
        if self._global_display:
            self._global_display.bank_name = bank.name if bank and bank.bank_count() > 1 else None

    def _scroll_bank(self, nav_position):
        bank = self._bank
        if not bank:
            return

        bank_count = bank.bank_count()
        new_index = bank.index
        if nav_position == NavPosition.First:
            new_index = 0
        elif nav_position == NavPosition.Prev:
            new_index = bank.index - 1
        elif nav_position == NavPosition.Next:
            new_index = bank.index + 1
        elif nav_position == NavPosition.Last:
            new_index = bank_count - 1
        
        new_index = clamp(new_index, 0, bank_count - 1)
        self._device_bank_registry.set_device_bank(self.device(), new_index)
