from __future__ import absolute_import, print_function, unicode_literals
from .utils import adjust_size
try:
  # Python 3
  from itertools import zip_longest
except ImportError:
  from itertools import izip_longest as zip_longest
from ableton.v2.control_surface.components import MixerComponent as MixerComponentBase
from ableton.v2.base import listens
import logging
from ableton.v2.control_surface.elements import DisplayDataSource

from .channel_strip_component import ChannelStripComponent

logger = logging.getLogger(__name__)

class MixerComponent(MixerComponentBase):
    _track_display = None
    _send_a_display = None
    _send_b_display = None
    _pan_display = None
    _global_display = None

    def __init__(self, *a, **k):
        super(MixerComponent, self).__init__(channel_strip_component_type=ChannelStripComponent, *a, **k)
        self._on_selected_track_changed()

    def set_send_controls(self, controls):
        self._send_controls = controls
        for strip, control in zip_longest(self._channel_strips, controls or []):
            if self._send_index is None:
                strip.set_send_controls(None)
            else:
                strip.set_send_controls(control)

    def set_monitor_buttons(self, buttons):
        for strip, button in zip_longest(self._channel_strips, buttons or []):
            strip.set_monitor_button(button)

    def set_launch_clip_buttons(self, buttons):
        for strip, button in zip_longest(self._channel_strips, buttons or []):
            strip.set_launch_clip_button(button)

    def set_stop_buttons(self, buttons):
        for strip, button in zip_longest(self._channel_strips, buttons or []):
            strip.set_stop_button(button)

    def set_track_display(self, display):
        #logger.info(u'SET TRACK DISPLAY: %s', display.__class__.__name__)
        self._track_display = display
        self._set_track_displays()

    def set_send_a_display(self, display):
        #logger.info(u'SET TRACK DISPLAY: %s', display.__class__.__name__)
        self._send_a_display = display
        self._set_track_displays()

    def set_send_b_display(self, display):
        #logger.info(u'SET TRACK DISPLAY: %s', display.__class__.__name__)
        self._send_b_display = display
        self._set_track_displays()

    def set_pan_display(self, display):
        #logger.info(u'SET TRACK DISPLAY: %s', display.__class__.__name__)
        self._pan_display = display
        self._set_track_displays()

    def set_global_display(self, display):
        self._global_display = display
        self._update_global_display()

    def _reassign_tracks(self):
        super(MixerComponent, self)._reassign_tracks()
        self._set_track_displays()

    def _on_selected_track_changed(self):
        self.__on_selected_track_name_changed.subject = self.selected_strip().track
        self._update_global_display()

    @listens(u'name')
    def __on_selected_track_name_changed(self):
        self._set_track_displays()

    def _update_global_display(self):
        if self._global_display is not None:
            self._global_display.track_name = self.song.view.selected_track.name if self.song.view.selected_track else None

    def _set_track_displays(self):
        tracks = self._track_assigner.tracks(self._provider)

        if self._track_display is not None:
            self._track_display.set_values([getattr(track, 'name', u'') for track in tracks])

        return_tracks = self.song.return_tracks
        master_track = self.song.master_track

        if self._send_a_display is not None:
            send_a_name = return_tracks[0].name[2:] if len(return_tracks) > 0 else u''
            self._send_a_display.set_values([send_a_name if t and t != master_track else u'' for t in tracks])

        if self._send_b_display is not None:
            send_b_name = return_tracks[1].name[2:] if len(return_tracks) > 1 else u''
            self._send_b_display.set_values([send_b_name if t and t != master_track else u'' for t in tracks])

        if self._pan_display is not None:
            pan_name = u'Pan'
            self._pan_display.set_values([pan_name if t else u'' for t in tracks])

        self._update_global_display()
 