from __future__ import absolute_import, print_function, unicode_literals
import logging
from bisect import insort
from ableton.v2.base import task, depends
from ableton.v2.control_surface.control_element import ControlElement
from ableton.v2.control_surface import SharedResource, NotifyingControlElement
from ableton.v2.control_surface.elements import ButtonElementMixin

from .consts import *

logger = logging.getLogger(__name__)

DEFAULT_DISPLAY_PRIORITY = 0 
GLOBAL_DISPLAY_PRIORITY = 1
PARAMETER_DISPLAY_PRIORITY = 2
MESSAGE_DISPLAY_PRIORITY = 3

def get_display_msg(text: str, offset=0):
    return (
        0xF0, 0, 0, 0,
        0x4E, 0x2C, 0x1B,
        0x4E, 0x22, 0x13,
        0x4A, 0x20 | (offset >> 4), 0x10 | (offset & 0xF),
        *[item for c in text for item in [0x4D, 0x20 | (ord(c) >> 4), 0x10 | (ord(c) & 0xF)]],
        0x4E, 0x22, 0x14,
        0xF7
    )

def fixed_length_string(text, length):
    if text is None:
        return " " * length
    if len(text) > length:
        return text[:length]
    return text.ljust(length)

def format_value(text):
    if text is None or text == "":
        return EMPTY_ROW_CONTENT
    return translate_string(text)[:DISPLAY_ROW_SIZE].center(DISPLAY_ROW_SIZE)

class FaderfoxTotalDisplay(ControlElement):
    _display_content = EMPTY_DISPLAY_CONTENT
    _visible = False

    def __init__(self, name="FaderfoxTotalDisplay", layers=[], *a, **k):
        super(FaderfoxTotalDisplay,self).__init__(name=name, optimized_send_midi=True, *a, **k)
        self._layers = sorted(layers, key=lambda l: -l._priority)
        for l in self._layers:
            l._total_display = self

    def add_layer(self, layer):
        insort(self._layers, layer, key=lambda l: -l._priority)
        layer._total_display = self
        return layer

    def update_display(self, force=False):
        layer = next((l for l in self._layers if l._visible), None)

        #logger.info("Faderfox Universal 2: Updating total display element, layer is {}".format(layer.name if layer is not None else None))

        if layer is None:
            if self._visible:
                self.send_midi(CLEAR_AND_HIDE_TOTAL_DISPLAY)
                self._display_content = EMPTY_DISPLAY_CONTENT
                self._visible = False
            return

        self._visible = True

        new_content = layer._display_content
        cur_content = self._display_content
        self._display_content = new_content

        if force:
            msg = get_display_msg(new_content)
            self.send_midi(msg)
            return

        if new_content == cur_content:
            return

        start = 0
        while start < DISPLAY_TOTAL_LENGTH and new_content[start] == cur_content[start]:
            start += 1
        end = DISPLAY_TOTAL_LENGTH - 1
        while end >= start and new_content[end] == cur_content[end]:
            end -= 1

        if start > end:
            return

        text_part = new_content[start : end + 1]
        msg = get_display_msg(text_part, start)
        self.send_midi(msg)

        #logger.info("Faderfox Universal 2: Updating value display element for index {}: '{}'".format(start // DISPLAY_ROW_SIZE, text_part))

    def reset(self):
        pass
    
class FaderfoxDisplayLayer(ControlElement):
    _priority = 0
    _display_content = EMPTY_DISPLAY_CONTENT
    _visible = False
    _total_display = None

    @depends(faderfox_settings=None)
    def __init__(self, priority=0, faderfox_settings=None, *a, **k):
        super(FaderfoxDisplayLayer,self).__init__(resource_type=SharedResource, *a, **k)
        assert faderfox_settings is not None
        self._settings = faderfox_settings
        self._priority = priority

    def show(self):
        if not self._visible:
            self._visible = True
            self._force_update_display()

    def hide(self):
        if self._visible:
            self._visible = False
            self._force_update_display()

    def _set_content(self, content):
        self._display_content = fixed_length_string(content, 80)
    
    def _force_update_display(self):
        if self._total_display:
            self._total_display.update_display()
            #logger.info("Faderfox Universal 2: Updating total display element from layer {}".format(self.name))

    def reset(self):
        pass
    

class FaderfoxGlobalDisplay(FaderfoxDisplayLayer):
    _device_name = "-"
    _bank_name = "-"
    _track_name = "-"

    _active_status = " "
    _lock_status = " "
    _show_status = " "

    def __init__(self, *a, **k):
        super(FaderfoxGlobalDisplay, self).__init__(priority=GLOBAL_DISPLAY_PRIORITY, name=u"FaderfoxGlobalDisplay", *a, **k)
        self._update()

    @property
    def track_name(self):
        return self._track_name

    @track_name.setter
    def track_name(self, value):
        self._track_name = translate_string(value or "-")
        self._update()

    @property
    def device_name(self):
        return self._device_name

    @device_name.setter
    def device_name(self, value):
        self._device_name = translate_string(value or "-")
        if not value:
            self._active_status = " "
            self._lock_status = " "
            self._show_status = " "
        self._update()

    @property
    def bank_name(self):
        return self._bank_name

    @bank_name.setter
    def bank_name(self, value):
        self._bank_name = translate_string(value or "-")
        self._update()

    @property
    def active_status(self):
        return self._active_status
    
    @active_status.setter
    def active_status(self, value):
        self._active_status = "*" if value else " "
        self._update()

    @property
    def lock_status(self):
        return self._lock_status
    
    @lock_status.setter
    def lock_status(self, value):
        self._lock_status = "*" if value else " "
        self._update()

    @property
    def show_status(self):
        return self._show_status
    
    @show_status.setter
    def show_status(self, value):
        self._show_status = "*" if value else " "
        self._update()

    def _update(self):
        lines = [EMPTY_ROW_CONTENT, EMPTY_ROW_CONTENT, EMPTY_ROW_CONTENT, EMPTY_ROW_CONTENT]
        lines[0] = GLOBAL_DISPLAY_ROW_TEMPLATE.format(label="Trk", name=self._track_name[:GLOBAL_DISPLAY_ROW_TEMPLATE_NAME_LENGTH])
        if self._device_name != "-":
            lines[1] = GLOBAL_DISPLAY_ROW_TEMPLATE.format(label="Dvc", name=self._device_name[:GLOBAL_DISPLAY_ROW_TEMPLATE_NAME_LENGTH])
            lines[3] = "Actv{active_status}Lock{lock_status}Show{show_status}View ".format(
                active_status=self._active_status, lock_status=self._lock_status, show_status=self._show_status)
        else:
            lines[3] = "               View "
        if self._bank_name != "-":
            lines[2] = GLOBAL_DISPLAY_ROW_TEMPLATE.format(label="Bnk", name=self._bank_name[:GLOBAL_DISPLAY_ROW_TEMPLATE_NAME_LENGTH])
        self._set_content("".join(lines))

    def show(self):
        if self._settings.global_display_enabled and self._settings.is_device_group:
            super().show()

class FaderfoxMessageDisplay(FaderfoxDisplayLayer):
    def __init__(self, *a, **k):
        super(FaderfoxMessageDisplay, self).__init__(priority=MESSAGE_DISPLAY_PRIORITY, name=u"FaderfoxGlobalDisplay", *a, **k)
        self._auto_hide_task = self._tasks.add(task.sequence(task.wait(1.0), task.run(self.hide)))
        self._auto_hide_task.kill()

    def show_message(self, *messages):
        content = "".join((format_value(messages[ix] if len(messages) > ix else None)) for ix in range(4))
        self._set_content(content)
        self.show()
        self._auto_hide_task.restart()


class FaderfoxParameterDisplay(FaderfoxDisplayLayer):
    _last_parameter = None

    def _create_hide_task(self, ix):
        return self._tasks.add(
            task.sequence(task.wait(0.5), task.run(lambda: self._hide_display(ix)))
        )

    def __init__(self, *a, **k):
        super(FaderfoxParameterDisplay, self).__init__(priority=PARAMETER_DISPLAY_PRIORITY, name=u"FaderfoxParameterDisplay", *a, **k)

        self._hide_tasks = [self._create_hide_task(ix) for ix in [0, 1]]
        self._parameter_slots = [None, None]
        self._line_content = [EMPTY_ROW_CONTENT, EMPTY_ROW_CONTENT, EMPTY_ROW_CONTENT, EMPTY_ROW_CONTENT]
        self._visible_parameters = set()

        for t in self._hide_tasks:
            t.kill()

    def _update_display(self):
        content = "".join(self._line_content)
        self._set_content(content)
        if content != EMPTY_DISPLAY_CONTENT:
            self.show()
        else:
            self.hide()

    def _set_line(self, index, text, star=False):
        text = format_value(text)
        if star:
            text = text[:-1] + "*"
        self._line_content[index] = text

    def show_parameter(self, parameter, auto_hide=True):
        slot = self._get_parameter_slot(parameter.name, True)

        self._set_line(slot * 2, parameter.name, not parameter.is_enabled)
        self._set_line(slot * 2 + 1, str(parameter))
        self._update_display()

        if auto_hide:
            if parameter.name not in self._visible_parameters:
                self._hide_tasks[slot].restart()
        else:
            self._hide_tasks[slot].kill()
            self._visible_parameters.add(parameter.name)

    def hide_parameter(self, parameter):
        slot = self._get_parameter_slot(parameter.name)
        if parameter.name in self._visible_parameters:
            self._visible_parameters.remove(parameter.name)
        if slot != -1:
            self._hide_display(slot)

    def auto_hide(self, parameter):
        slot = self._get_parameter_slot(parameter.name)
        if slot != -1:
            if parameter.name in self._visible_parameters:
                self._visible_parameters.remove(parameter.name)
            self._hide_tasks[slot].restart()

    def update_parameter_value(self, parameter):
        slot = self._get_parameter_slot(parameter.name)

        if slot != -1:
            self._set_line(slot * 2 + 1, str(parameter))
            self._update_display()

    def _get_parameter_slot(self, name, allocate=False):
        last_parameter = self._last_parameter
        if allocate:
            self._last_parameter = name

        if self._parameter_slots[0] == name:
            return 0
        elif self._parameter_slots[1] == name:
            return 1
        elif not allocate:
            return -1

        if self._parameter_slots[0] is None:
            slot = 0
        elif self._parameter_slots[1] is None:
            slot = 1
        elif self._parameter_slots[0] in self._visible_parameters:
            slot = 1
        elif self._parameter_slots[1] in self._visible_parameters:
            slot = 0
        elif self._parameter_slots[0] == last_parameter:
            slot = 1
        else:
            slot = 0

        self._parameter_slots[slot] = name
        return slot

    def _hide_display(self, index):
        self._hide_tasks[index].kill()
        if self._parameter_slots[index] in self._visible_parameters:
            return
        self._parameter_slots[index] = None
        self._set_line(index * 2, None)
        self._set_line(index * 2 + 1, None)
        self._update_display()

    def reset_display(self):
        for t in self._hide_tasks:
            t.kill()
        self._visible_parameters.clear()
        self._parameter_slots = [None, None]
        self._line_content = [EMPTY_ROW_CONTENT, EMPTY_ROW_CONTENT, EMPTY_ROW_CONTENT, EMPTY_ROW_CONTENT]
        self._display_content = EMPTY_DISPLAY_CONTENT
        self._last_parameter = None
        self.hide()

    def reset(self):
        self.reset_display()
