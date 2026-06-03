from __future__ import absolute_import, print_function, unicode_literals
import logging
from ableton.v2.base import liveobj_valid, clamp
from ableton.v2.control_surface.control import ButtonControl, ToggleButtonControl
from ableton.v2.control_surface.components import ChannelStripComponent as ChannelStripComponentBase
from ableton.v2.control_surface.elements import Color
from itertools import chain

from .utils import index_of

logger = logging.getLogger(__name__)


def switch_monitor_track(track):
    track.current_monitoring_state = (
        track.current_monitoring_state + 1) % len(track.monitoring_states.values)


class ChannelStripComponent(ChannelStripComponentBase):
    launch_clip_button = ButtonControl()
    stop_button = ButtonControl()
    monitor_button = ToggleButtonControl()
    _monitor_connected = False
    _clip_slot = None

    def __init__(self, *a, **k):
        super(ChannelStripComponent, self).__init__(*a, **k)
        self.song.view.add_selected_scene_listener(self._on_clip_slot_change)

    def disconnect(self):
        self.song.view.remove_selected_scene_listener(
            self._on_clip_slot_change)

        if liveobj_valid(self._track) and self._monitor_connected:
            self._monitor_connected = False
            self._track.remove_current_monitoring_state_listener(
                self._on_monitor_changed)
            #self._track.remove_playing_slot_index_listener(
            #    self._on_playing_slot_index_changed)

        self._unregister_clip_slot()

        super(ChannelStripComponent, self).disconnect()

    def _is_mastertrack(self):
        return self._track == self.song.master_track

    def _is_returntrack(self):
        return self._track in self.song.return_tracks

    #def set_mute_button(self, button):
        #if self._is_mastertrack():
            #return
    #    super(ChannelStripComponent, self).set_mute_button(button)

    #def set_solo_button(self, button):
        #if self._is_mastertrack():
            #return
    #    super(ChannelStripComponent, self).set_solo_button(button)

    #def set_arm_button(self, button):
        #if self._is_mastertrack() or self._is_returntrack():
            #return
    #    super(ChannelStripComponent, self).set_arm_button(button)

    def set_monitor_button(self, button):
        #if self._is_mastertrack() or self._is_returntrack():
            #return
        if self.monitor_button._control_element != button:
            self.monitor_button.set_control_element(button)

    def _solo_value(self, value):
        if self._is_mastertrack():
            #logger.info(u'ignoring solo value for master/return track')
            self._on_solo_changed()
            return
        super(ChannelStripComponent, self)._solo_value(value)

    def _arm_value(self, value):
        if self._is_mastertrack() or self._is_returntrack():
            self._arm_button.send_value(0, False)
            #logger.info(u'ignoring arm value for master/return track')
            self._on_arm_changed()
            return
        super(ChannelStripComponent, self)._arm_value(value)

    def set_track(self, track):
        if liveobj_valid(self._track) and self._monitor_connected:
            self._monitor_connected = False
            self._track.remove_current_monitoring_state_listener(
                self._on_monitor_changed)
            
        self._unregister_clip_slot()

        super(ChannelStripComponent, self).set_track(track)

        self._register_clip_slot()

        if self.has_monitor():
            self._track.add_current_monitoring_state_listener(
                self._on_monitor_changed)
            self._monitor_connected = True
        else:
            self._monitor_connected = False

        self.button_update()

    def button_update(self):
        monitor_button_enabled = False
        launch_clip_button_enabled = False
        stop_button_enabled = False

        if self._track in self.song.tracks:
            if self._track.can_be_armed:
                monitor_button_enabled = True
            launch_clip_button_enabled = True
            stop_button_enabled = True

        self.monitor_button.enabled = monitor_button_enabled
        self.launch_clip_button.enabled = launch_clip_button_enabled
        self.stop_button.enabled = stop_button_enabled

        self._on_clip_slot_change()

    def _on_playing_slot_index_changed(self):
        if self.stop_button._control_element == None:
            return

        light = u'Mixer.StopOn'
        for clip_slot in self._track.clip_slots:
            if clip_slot.is_playing or clip_slot.is_triggered:
                light = u'Mixer.StopOff'
                break

        # logger.info(u'set track to {}'.format(light))

        self.stop_button._control_element.set_light(light)

    def _on_clip_slot_change(self):
        self._register_clip_slot()
        self._on_clip_changed()


    def _register_clip_slot(self):
        self._unregister_clip_slot()

        if not self._track in self.song.tracks:
            return

        scene = self.song.view.selected_scene
        track_idx = index_of(self.song.tracks, self._track)

        self._clip_slot = scene.clip_slots[track_idx]
        self._clip_slot.add_playing_status_listener(self._on_clip_changed)
        self._clip_slot.add_has_clip_listener(self._on_clip_changed)
        self._clip_slot.add_is_triggered_listener(self._on_clip_changed)

        self._track.add_playing_slot_index_listener(self._on_clip_changed)
        self._track.add_fired_slot_index_listener(self._on_clip_changed)

    def _unregister_clip_slot(self):
        if self._clip_slot == None:
            return

        self._track.remove_fired_slot_index_listener(self._on_clip_changed)
        self._track.remove_playing_slot_index_listener(self._on_clip_changed)

        self._clip_slot.remove_is_triggered_listener(self._on_clip_changed)
        self._clip_slot.remove_has_clip_listener(self._on_clip_changed)
        self._clip_slot.remove_playing_status_listener(self._on_clip_changed)
        self._clip_slot = None

    @monitor_button.pressed
    def _monitor_button(self, button):
        switch_monitor_track(self._track)

    def update(self):
        super(ChannelStripComponent, self).update()
        self._on_monitor_changed()
        self._on_clip_changed()

    def has_monitor(self):
        return liveobj_valid(self._track) and self._track in self.song.tracks and self._track.can_be_armed

    def _on_monitor_changed(self):
        self._on_clip_changed()
        #if self.is_enabled() and self.monitor_button._control_element != None:
        if self.has_monitor():
            monitoring_state = self._track.current_monitoring_state
            # logger.info(u'set monitoring color to {}'.format(monitoring_state))
            self.monitor_button.is_toggled = True if monitoring_state == 0 or monitoring_state == 1 else False
        else:
            self.monitor_button.is_toggled = False

    def set_launch_clip_button(self, button):
        self.launch_clip_button.set_control_element(button)

    @launch_clip_button.pressed
    def _launch_clip_button(self, button):
        scene = self.song.view.selected_scene
        track_idx = index_of(self.song.tracks, self._track)

        if len(scene.clip_slots) > track_idx:
            clip_slot = scene.clip_slots[track_idx]
            clip_slot.set_fire_button_state(True)

    def _on_clip_changed(self):
        if not self.is_enabled():
            return

        launch_button = self.launch_clip_button._control_element
        # stop_button = self.stop_button._control_element

        if launch_button == None: # or stop_button == None:
            return

        scene = self.song.view.selected_scene
        track_idx = index_of(self.song.tracks, self._track)

        if not self._track in self.song.tracks:
            launch_button.set_light(u'Mixer.ClipEmpty')
            # stop_button.set_light(u'Mixer.StopOn')
            return

        self._on_playing_slot_index_changed()

        clip_slot = scene.clip_slots[track_idx]
        # logger.info(u'playing status of clip {}: playing: {}, triggered: {}, status: {}'.format(track_idx, clip_slot.is_playing, clip_slot.is_triggered, clip_slot.playing_status))
        if clip_slot.is_playing:
            launch_button.set_light(u'Mixer.ClipStarted')
            # stop_button.set_light(u'Mixer.StopOff')
        elif clip_slot.has_clip:
            launch_button.set_light(u'Mixer.ClipStopped')
            # stop_button.set_light(u'Mixer.StopOn')
        else:
            launch_button.set_light(u'Mixer.ClipEmpty')
            # stop_button.set_light(u'Mixer.StopOn')

    def set_stop_button(self, button):
        self.stop_button.set_control_element(button)

    @stop_button.pressed
    def _stop_button(self, button):
        self._track.stop_all_clips()

    _last_cf = 0

    def _crossfade_toggle_value(self, value):
        if self.is_enabled():
            if liveobj_valid(self._track):
                old_value = self._track.mixer_device.crossfade_assign
                new_value = clamp(
                    old_value + (1 if value > self._last_cf or value == 127 else -1), 0, 2)
                if old_value != new_value:
                    self._track.mixer_device.crossfade_assign = new_value
                    self._on_cf_assign_changed()
                self._last_cf = value

    def _on_cf_assign_changed(self):
        if self.is_enabled() and self._crossfade_toggle != None:
            if liveobj_valid(self._track) and self._track in chain(self.song.tracks, self.song.return_tracks):
                if self._track.mixer_device.crossfade_assign == 0:
                    self._crossfade_toggle.send_value(0, True)
                elif self._track.mixer_device.crossfade_assign == 2:
                    self._crossfade_toggle.send_value(127, True)
                else:
                    self._crossfade_toggle.send_value(63, True)
