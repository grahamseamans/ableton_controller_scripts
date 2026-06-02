from __future__ import absolute_import, print_function, unicode_literals
from itertools import zip_longest
from functools import partial
from ableton.v2.control_surface.components import DisplayingDeviceParameterComponent as DisplayingDeviceParameterComponentBase
from ableton.v2.control_surface.control import ControlList, MappedSensitivitySettingControl, ToggleButtonControl, ButtonControl, control_list
from ableton.v2.control_surface.elements import DisplayDataSource, adjust_string
from ableton.v2.base import depends, listens, liveobj_valid, listens_group
import logging

logger = logging.getLogger(__name__)

VIEW_SESSION = u'Session'
VIEW_ARRANGER = u'Arranger'
VIEW_CLIP = u'Detail/Clip'
VIEW_DEVICE_CHAIN = u'Detail/DeviceChain'
VIEW_DETAIL = u'Detail'

MAPPINGS4 = {
    "Macro 10": "Mc10",
    "Macro 11": "Mc11",
    "Macro 12": "Mc12",
    "Macro 13": "Mc13",
    "Macro 14": "Mc14",
    "Macro 15": "Mc15",
    "Macro 16": "Mc16",
}

def adj(original, length):
    return MAPPINGS4.get(original, adjust_string(original, length)) if length == 4 else adjust_string(original, length)

ENCODER_COUNT = 16

class FaderfoxMappedSensitivitySettingControl(MappedSensitivitySettingControl):
    class State(MappedSensitivitySettingControl.State):
        def _update_direct_connection(self):
            super()._update_direct_connection()
            if self._control_element and hasattr(self._control_element, 'connect_to_direct'):
                self._control_element.connect_to_direct(self._direct_mapping)

class DisplayingDeviceParameterComponent(DisplayingDeviceParameterComponentBase):
    device_lock_button = ToggleButtonControl()
    device_on_off_button = ToggleButtonControl()
    rack_show_hide_button = ToggleButtonControl()
    device_show_hide_button = ToggleButtonControl()
    view_toggle_button = ToggleButtonControl()
    show_parameter_controls = control_list(ButtonControl, 16)

    _device_parameter_display = None
    _global_display = None
    _message_display = None
    show_global_display_button = ButtonControl()

    controls = ControlList(FaderfoxMappedSensitivitySettingControl, ENCODER_COUNT)

    @depends(device_provider=None,faderfox_settings=None)
    def __init__(self, device_provider = None, faderfox_settings=None, toggle_lock = None, *a, **k):
        super(DisplayingDeviceParameterComponent, self).__init__(*a, **k)
        self._parameter_name_data_sources = [DisplayDataSource(u'', adjust_string_fn=adj) for _ in range(ENCODER_COUNT)]
        self._parameter_value_data_sources = [DisplayDataSource(u'') for _ in range(ENCODER_COUNT)]
        assert toggle_lock is not None
        assert faderfox_settings is not None

        self._toggle_lock = toggle_lock
        self._device_provider = device_provider

        self._settings = faderfox_settings

        self.__on_provided_device_changed.subject = device_provider
        self.__on_provided_device_changed()

        self.__on_is_locked_to_device_changed.subject = self._device_provider
        self.__on_is_locked_to_device_changed()

        view = self.application.view
        self.__on_device_chain_view_visibility_changed.subject = view
        self.__on_device_view_visibility_changed.subject = view 
        self._update_device_show_hide_button()

        self.__on_session_view_visibility_changed.subject = view
        self.__on_session_view_visibility_changed()

    def set_device_parameter_display(self, display):
        #logger.info(u'Faderfox Universal 2: Setting total device display.')
        self._device_parameter_display = display

    def set_message_display(self, display):
        self._message_display = display

    def set_global_display(self, display):
        self._global_display = display
        self._update_global_display()

    @show_global_display_button.pressed
    def _on_show_global_display_button_pressed(self, button):
        if self._global_display:
            self._global_display.show()

    @show_global_display_button.released
    def _on_show_global_display_button_released(self, button):
        if self._global_display:
            self._global_display.hide()

    @view_toggle_button.toggled
    def _view_toggle_button(self, *_):
        view = self.application.view
        #logger.info(u'VIEWS: {}'.format(u','.join(view.available_main_views())))
        view.show_view(VIEW_SESSION if not view.is_view_visible(VIEW_SESSION) else VIEW_ARRANGER)

    def _update_view_toggle_button(self):
        self.view_toggle_button.is_toggled = self.application.view.is_view_visible(VIEW_SESSION)

    @listens(u'is_view_visible', u'Session')
    def __on_session_view_visibility_changed(self):
        self._update_view_toggle_button()

    @device_lock_button.toggled
    def _device_lock_button(self, *_):
        self._on_device_lock_button_toggled()

    @device_on_off_button.toggled
    def _device_on_off_button(self, is_toggled, _):
        parameter = self._on_off_parameter()
        if parameter is not None:
            parameter.value = float(is_toggled)

    @device_show_hide_button.toggled
    def _device_show_hide_button(self, *_):
        if liveobj_valid(self._device):
            self._device.view.is_collapsed = not self._device.view.is_collapsed

    def _on_device_lock_button_toggled(self):
        self._toggle_lock()
        self._update_device_lock_button()

    def _update_device_lock_button(self):
        locked = self._device_provider.is_locked_to_device
        self.device_lock_button.is_toggled = locked
        if self._global_display:
            self._global_display.lock_status = locked
        
    def _update_global_display(self):
        if self._global_display:
            if liveobj_valid(self._device):
                self._global_display.device_name = self._device.name 
                self._global_display.show_status = not self._device.view.is_collapsed
            else:
                self._global_display.device_name = None
        self._update_device_lock_button()
        self._update_device_on_off_button()

    @listens(u'device')
    def __on_provided_device_changed(self):
        #logger.info("__on_provided_device_changed")
        self._device = self._device_provider.device
        self._update_device_lock_button()

        self.__on_device_on_off_changed.subject = self._on_off_parameter()
        self._update_device_on_off_button()

        if liveobj_valid(self._device):
            self.__on_device_is_collapsed_changed.subject = self._device.view
            self._update_device_is_shown()

        if self._device_parameter_display:
            self._device_parameter_display.reset_display()

        self.__on_device_name_changed.subject = self._device

        self._update_global_display()

    def _update_device_is_shown(self):
        self._device_show_hide_button.is_toggled = not self._device.view.is_collapsed
        if self._global_display:
            self._global_display.show_status = not self._device.view.is_collapsed

    @listens(u'is_collapsed')
    def __on_device_is_collapsed_changed(self):
        self._update_device_is_shown()

    @listens(u'is_locked_to_device')
    def __on_is_locked_to_device_changed(self):
        self._update_device_lock_button()

    @listens(u'value')
    def __on_device_on_off_changed(self):
        #if self._message_display:
            #self._message_display.show_message(u'Device On/Off:', "{}".format(self._on_off_parameter().value))
        self._update_device_on_off_button()

    @listens(u'name')
    def __on_device_name_changed(self):
        #logger.info(u'Faderfox Universal 2: Device name changed: {}'.format(self._device.name))
        self._update_global_display()

    def _on_off_parameter(self):
        if liveobj_valid(self._device):
            for p in self._device.parameters:
                if p.name.startswith(u'Device On') and liveobj_valid(p) and p.is_enabled:
                    return p

    def _update_device_on_off_button(self):
        parameter = self._on_off_parameter()
        self.device_on_off_button.enabled = parameter is not None
        if parameter is not None:
            self.device_on_off_button.is_toggled = parameter.value > 0
        if self._global_display:
            self._global_display.active_status = parameter.value > 0 if parameter is not None else False

    @rack_show_hide_button.toggled
    def _show_device_chain(self, *_):
        view = self.application.view
        view.show_view(VIEW_DETAIL)
        view.show_view(VIEW_DEVICE_CHAIN if not view.is_view_visible(VIEW_DEVICE_CHAIN) else VIEW_CLIP)

    def _update_device_show_hide_button(self):
        view = self.application.view
        self.rack_show_hide_button.is_toggled = view.is_view_visible(VIEW_DETAIL) and view.is_view_visible(VIEW_DEVICE_CHAIN)

    @listens(u'is_view_visible', u'Detail/DeviceChain')
    def __on_device_chain_view_visibility_changed(self):
        self._update_device_show_hide_button()

    @listens(u'is_view_visible', u'Detail')
    def __on_device_view_visibility_changed(self):
        self._update_device_show_hide_button()
    
    @listens_group(u'value')
    def _on_parameter_value_changed(self, parameter):
        if self.is_enabled() and self._device_parameter_display is not None:
            self._device_parameter_display.update_parameter_value(parameter)
            #logger.info(u'Faderfox Universal 2: Parameter value changed: {}'.format(parameter.name))

    @show_parameter_controls.pressed
    def _on_show_parameter_controls_pressed(self, button):
        if not self._settings.perm_param_display:
            return

        #logger.info("Faderfox Universal 2: Show parameter control pressed {}".format(button.index))
        if self._device_parameter_display and len(self.parameters) > button.index:
            self._device_parameter_display.show_parameter(self.parameters[button.index], False)

    @show_parameter_controls.released_delayed
    def _on_show_parameter_controls_released_delayed(self, button):
        #logger.info("Faderfox Universal 2: Show parameter control released {}".format(button.index))
        if self._device_parameter_display and len(self.parameters) > button.index:
            self._device_parameter_display.hide_parameter(self.parameters[button.index])

    @show_parameter_controls.released_immediately
    def _on_show_parameter_controls_released(self, button):
        #logger.info("Faderfox Universal 2: Show parameter control released immediately {}".format(button.index))
        if len(self.parameters) > button.index:
            parameter = self.parameters[button.index]

            if self._device_parameter_display:
                self._device_parameter_display.auto_hide(parameter)

            if not parameter.is_quantized and self._settings.set_defaults:
                parameter.value = parameter.default_value
