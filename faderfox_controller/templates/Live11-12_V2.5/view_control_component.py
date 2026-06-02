from __future__ import absolute_import, print_function, unicode_literals
import logging
from Faderfox_Universal_2.consts import NavPosition
from ableton.v2.base import clamp
from ableton.v2.control_surface.components import ViewControlComponent as ViewControlComponentBase
from ableton.v2.control_surface.control import ButtonControl

from .utils import index_of
from .send_control import SendValueEncoderControl

logger = logging.getLogger(__name__)

CLIP_VIEW = u'Detail/Clip'
TRACK_VIEW = u'Detail/DeviceChain'
ARRANGER_VIEW = u'Arranger'
SESSION_VIEW = u'Session'

COLOR_ON = u'DefaultButton.On'
COLOR_OFF = u'DefaultButton.Off'

class ViewControlComponent(ViewControlComponentBase):
    clip_view_button = ButtonControl()
    track_view_button = ButtonControl()
    track_select_encoder = SendValueEncoderControl()
    scene_select_encoder = SendValueEncoderControl()
    arranger_view_button = ButtonControl()
    first_track_button = ButtonControl()
    prev_track_button = ButtonControl()
    next_track_button = ButtonControl()
    last_track_button = ButtonControl()

    def __init__(self, session_ring = None, *a, **k):
        super(ViewControlComponent, self).__init__(*a, **k)

        self._session_ring = session_ring

        app_view = self.application.view
        app_view.add_is_view_visible_listener(CLIP_VIEW, self._on_clip_view_visible_changed)
        app_view.add_is_view_visible_listener(TRACK_VIEW, self._on_track_view_visible_changed)

        song_view = self.song.view
        song_view.add_selected_scene_listener(self._on_selected_scene_changed)
        song_view.add_selected_track_listener(self._on_selected_track_changed)

        self._on_clip_view_visible_changed()
        self._on_track_view_visible_changed()
        self._on_selected_scene_changed()
        self._on_selected_track_changed()

    def disconnect(self):
        super(ViewControlComponent, self).disconnect()

        app_view = self.application.view
        app_view.remove_is_view_visible_listener(CLIP_VIEW, self._on_clip_view_visible_changed)
        app_view.remove_is_view_visible_listener(TRACK_VIEW, self._on_track_view_visible_changed)

        song_view = self.song.view
        song_view.remove_selected_scene_listener(self._on_selected_scene_changed)
        song_view.remove_selected_track_listener(self._on_selected_track_changed)

    def _on_clip_view_visible_changed(self):
        app_view = self.application.view
        self.clip_view_button.color = COLOR_ON if app_view.is_view_visible(CLIP_VIEW) else COLOR_OFF

    def _on_track_view_visible_changed(self):
        app_view = self.application.view
        self.track_view_button.color = COLOR_ON if app_view.is_view_visible(TRACK_VIEW) else COLOR_OFF

    @clip_view_button.pressed
    def _clip_view_button(self, button):
        self.show_view(CLIP_VIEW)

    @track_view_button.pressed
    def _track_view_button(self, button):
        self.show_view(TRACK_VIEW)

    @arranger_view_button.pressed
    def arranger_view_button(self, button):
        if self.application.view.is_view_visible(ARRANGER_VIEW):
            self.show_view(SESSION_VIEW)
        else:
            self.show_view(ARRANGER_VIEW)

    @scene_select_encoder.value
    def scene_select_encoder(self, value, encoder):
        index = self._set_selected_scene_index(
            self._get_selected_scene_index() + int(round(value * 64.0)))
        encoder.value = index + 1

    def _on_selected_scene_changed(self):
        index = self._get_selected_scene_index()
        if index >= 0:
            self.scene_select_encoder.value = index + 1

    def _get_selected_scene_index(self):
        selected_scene = self.song.view.selected_scene
        return index_of(self.song.scenes, selected_scene)
        pass

    def _set_selected_scene_index(self, index):
        scenes = self.song.scenes
        index = clamp(index, 0, len(scenes) - 1)
        self.song.view.selected_scene = scenes[index]
        return index

    @track_select_encoder.value
    def track_select_encoder(self, value, encoder):
        index = self._set_selected_track_index(int(round(value * 64.0)))
        encoder.value = index + 1

    @first_track_button.pressed
    def _first_track_button(self, button):
        self._set_selected_track_index(NavPosition.First)

    @prev_track_button.pressed
    def _prev_track_button(self, button):
        self._set_selected_track_index(NavPosition.Prev)

    @next_track_button.pressed
    def _next_track_button(self, button):
        self._set_selected_track_index(NavPosition.Next)

    @last_track_button.pressed
    def _last_track_button(self, button):
        self._set_selected_track_index(NavPosition.Last)

    def _get_selected_track_index(self):
        selected_track = self.song.view.selected_track
        return index_of(self._session_ring.tracks_to_use(), selected_track)

    def _set_selected_track_index(self, nav_position):
        tracks = self._session_ring.tracks_to_use()

        index = self._get_selected_track_index()
        increment = 1
        if nav_position == NavPosition.First:
            index = 0
        elif nav_position == NavPosition.Prev:
            index -= 1
            increment = -1
        elif nav_position == NavPosition.Next:
            index += 1
        elif nav_position == NavPosition.Last:
            index = len(tracks) - 1
            increment = -1

        index = clamp(index, 0, len(tracks) - 1)
        track = tracks[index]
        if track.is_visible == False:
            while track.is_visible == False:
                index += increment
                track = tracks[index]

        self.song.view.selected_track = track
        return index

    def _on_selected_track_changed(self):
        index = self._get_selected_track_index()
        if index >= 0:
            self.track_select_encoder.value = index + 1
