import logging
from ableton.v2.base import depends
from ableton.v2.control_surface import Component
from ableton.v2.control_surface.control import ButtonControl

logger = logging.getLogger(__name__)

class FaderfoxEc4Settings:
    temp_param_display = True
    perm_param_display = True
    set_defaults = True
    global_display_enabled = True

    is_device_group = False
    setup = 0
    group = 0

class FaderfoxEc4SettingComponent(Component):
    _settings = FaderfoxEc4Settings()

    temp_param_display_button = ButtonControl()
    perm_param_display_button = ButtonControl()
    set_defaults_button = ButtonControl()
    global_display_button = ButtonControl()

    _message_display = None

    @depends(faderfox_settings=None)
    def __init__(self, faderfox_settings=None, show_message=None, *a, **k):
        super().__init__(*a, **k)
        assert faderfox_settings is not None
        self._settings = faderfox_settings
        self._show_message = show_message

    def set_message_display(self, display):
        self._message_display = display

    def show_message(self, *messages):
        logger.info("".join(messages))
        if self._show_message:
            self._show_message("".join(messages))
        if self._message_display:
            self._message_display.show_message(*messages)

    @temp_param_display_button.released_immediately
    def _temp_param_display_button(self, _):
        self._settings.temp_param_display = True
        self.show_message("temporary parameter display:", "on")
    
    @temp_param_display_button.released_delayed
    def _temp_param_display_button_delayed(self, _):
        self._settings.temp_param_display = False
        self.show_message("temporary parameter display:", "off")

    @perm_param_display_button.released_immediately
    def _perm_param_display_button(self, _):
        self._settings.perm_param_display = True
        self.show_message("permanent parameter display:", "on")

    @perm_param_display_button.released_delayed
    def _perm_param_display_button_delayed(self, _):
        self._settings.perm_param_display = False
        self.show_message("permanent parameter display:", "off")

    @set_defaults_button.released_immediately
    def _set_defaults_button(self, _):
        self._settings.set_defaults = True
        self.show_message("set defaults:", "on")

    @set_defaults_button.released_delayed
    def _set_defaults_button_delayed(self, _):
        self._settings.set_defaults = False
        self.show_message("set defaults:", "off")

    @global_display_button.released_immediately
    def _global_display_button(self, _):
        self._settings.global_display_enabled = True
        self.show_message("global display:", "on")

    @global_display_button.released_delayed
    def _global_display_button_delayed(self, _):
        self._settings.global_display_enabled = False
        self.show_message("global display:", "off")
