from __future__ import absolute_import, print_function, unicode_literals
import Live
import logging
from ableton.v2.base import listens, clamp
from ableton.v2.control_surface.components import TransportComponent as TransportComponentBase
from ableton.v2.control_surface.components.transport import TEMPO_TOP, TEMPO_BOTTOM
from ableton.v2.control_surface.control import ButtonControl, Control

from .utils import normalize_relative_value, index_of
from .send_control import SendValueControl, SendValueEncoderControl

logger = logging.getLogger(__name__)

MIN_TEMPO = 20.0
MAX_TEMPO = 999.0

quantizations = [
    Live.Song.Quantization.q_no_q,
    Live.Song.Quantization.q_8_bars,
    Live.Song.Quantization.q_4_bars,
    Live.Song.Quantization.q_2_bars,
    Live.Song.Quantization.q_bar,
    Live.Song.Quantization.q_half,
    Live.Song.Quantization.q_half_triplet,
    Live.Song.Quantization.q_quarter,
    Live.Song.Quantization.q_quarter_triplet,
    Live.Song.Quantization.q_eight,
    Live.Song.Quantization.q_eight_triplet,
    Live.Song.Quantization.q_sixtenth,
    Live.Song.Quantization.q_sixtenth_triplet,
    Live.Song.Quantization.q_thirtytwoth
]


def change_tempo(song, delta):
    song.tempo = round(clamp(song.tempo + delta, MIN_TEMPO, MAX_TEMPO), 2)


class TransportComponent(TransportComponentBase):

    launch_selected_scene_button = ButtonControl()
    stop_selected_scene_button = ButtonControl()
    quantization_control = SendValueEncoderControl()  # StepEncoderControl(32)
    tempo_display_control = SendValueControl()

    def __init__(self, *a, **k):
        super(TransportComponent, self).__init__(*a, **k)
        self.song.add_clip_trigger_quantization_listener(
            self._on_quantization_value_changed)
        self.song.add_tempo_listener(self._on_tempo_value_changed)
        self._on_quantization_value_changed()

    def disconnect(self):
        self.song.remove_tempo_listener(self._on_tempo_value_changed)
        self.song.remove_clip_trigger_quantization_listener(
            self._on_quantization_value_changed)
        super(TransportComponent, self).disconnect()

    def set_tempo_control(self, control, *a, **k):
        if control.message_map_mode() == Live.MidiMap.MapMode.absolute:
            return super(TransportComponent, self).set_tempo_control(control, *a, **k)

        if self._tempo_control != control:
            self._tempo_control = control
            self.__tempo_value.subject = control

    def set_tempo_fine_control(self, fine_control):
        if fine_control.message_map_mode() == Live.MidiMap.MapMode.absolute:
            return super(TransportComponent, self).set_tempo_fine_control(fine_control)

        if self._tempo_fine_control != fine_control:
            self._tempo_fine_control = fine_control
            self.__tempo_fine_value.subject = fine_control
            self._fine_tempo_needs_pickup = True
            self._prior_fine_tempo_value = -1

    @listens(u'value')
    def __tempo_value(self, value):
        if self._tempo_control.message_map_mode() == Live.MidiMap.MapMode.absolute:
            return super(TransportComponent, self).__tempo_value(value)

        if self.is_enabled():
            change_tempo(self.song, normalize_relative_value(value))

    @listens(u'value')
    def __tempo_fine_value(self, value):
        if self._tempo_fine_control.message_map_mode() == Live.MidiMap.MapMode.absolute:
            return super(TransportComponent, self).__tempo_value(value)

        if self.is_enabled():
            change_tempo(self.song, normalize_relative_value(value) * 0.01)

    @launch_selected_scene_button.pressed
    def _launch_selected_scene_button(self, button):
        self.song.view.selected_scene.set_fire_button_state(True)

    @stop_selected_scene_button.pressed
    def _stop_selected_scene_button(self, button):
        self.song.stop_all_clips()

    def _get_quantization_index(self):
        q = self.song.clip_trigger_quantization
        return index_of(quantizations, q)

    def _on_quantization_value_changed(self):
        index = self._get_quantization_index()
        if index != -1:
            self.quantization_control.value = index

    @quantization_control.value
    def _quantization_control(self, value, encoder):
        index = value
        # index = self._get_quantization_index() + value
        self.song.clip_trigger_quantization = clamp(
            index, 0, len(quantizations) - 1)

    def _on_tempo_value_changed(self):
        #logger.info(u'song tempo changed to {}'.format(self.song.tempo))
        # logger.info(u'TEMPO CHANGED TO: {}'.format(tempo))
        tempo = int(round(self.song.tempo, 2) * 10)
        self.tempo_display_control.value = tempo
