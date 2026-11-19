# -*- coding: utf-8 -*-
"""Drum maps: which note each voice pad writes, per drum plugin. The single source of notes.

PURE PYTHON, duck-typed (no Live import). Self-check: `uv run python drum_maps/__init__.py`.

  Voice(name, note, also_matches=())  - the sequencer writes `note` and reads the lane as
                                        {note} | also_matches (nudge and clear act on that set).
  DrumMap(name, device_names, voices) - <= 16 voices in pad order (row-major, top-left first).
  find_drum_map_for_track(track)      - the first device on the track whose .name matches a
                                        map's device_names (case-insensitive), else None.
"""

from __future__ import absolute_import, print_function, unicode_literals

try:
    from . import drumazon2, microtonic
except ImportError:
    import drumazon2
    import microtonic

MAXIMUM_VOICE_COUNT = 16


class Voice(object):

    def __init__(self, name, note, also_matches=()):
        for candidate_note in (note,) + tuple(also_matches):
            if not (0 <= candidate_note <= 127):
                raise ValueError("voice {0!r}: note {1!r} out of 0..127".format(name, candidate_note))
        self.name = name
        self.note = note
        self.also_matches = tuple(also_matches)
        self.lane_notes = frozenset((note,) + self.also_matches)

    def __repr__(self):
        return "Voice({0!r}, {1}, also_matches={2})".format(self.name, self.note, self.also_matches)


class DrumMap(object):

    def __init__(self, name, device_names, voices):
        voices = tuple(voices)
        if not voices or len(voices) > MAXIMUM_VOICE_COUNT:
            raise ValueError("drum map {0!r} needs 1..16 voices, got {1}".format(name, len(voices)))
        claimed_notes = set()
        for voice in voices:
            overlap = claimed_notes & voice.lane_notes
            if overlap:
                raise ValueError("drum map {0!r}: notes {1} claimed by two voices".format(name, sorted(overlap)))
            claimed_notes |= voice.lane_notes
        self.name = name
        self.device_names = tuple(device_names)
        self.lowercase_device_names = frozenset(device_name.lower() for device_name in device_names)
        self.voices = voices

    def voice_at_pad_index(self, pad_index):
        """The voice on voice pad `pad_index` (0..15), or None for an unused pad."""
        if 0 <= pad_index < len(self.voices):
            return self.voices[pad_index]
        return None

    def matches_device_name(self, device_name):
        return device_name.lower() in self.lowercase_device_names

    def __repr__(self):
        return "DrumMap({0!r})".format(self.name)


def _drum_map_from_data_module(data_module):
    return DrumMap(
        name=data_module.NAME,
        device_names=data_module.DEVICE_NAMES,
        voices=tuple(
            Voice(voice_name, note, also_matches=also_matches)
            for voice_name, note, also_matches in data_module.VOICES
        ),
    )


DRUM_MAP_REGISTRY = (
    _drum_map_from_data_module(drumazon2),
    _drum_map_from_data_module(microtonic),
)


def find_drum_map_for_track(track):
    """The DrumMap of the first top-level device on `track` whose .name matches, else None.

    Only the track's own device list is searched (not inside racks)."""
    for device in track.devices:
        for drum_map in DRUM_MAP_REGISTRY:
            if drum_map.matches_device_name(device.name):
                return drum_map
    return None


def _self_check():
    all_device_names = [name.lower() for drum_map in DRUM_MAP_REGISTRY for name in drum_map.device_names]
    assert len(all_device_names) == len(set(all_device_names)), "a device name is claimed by two maps"

    class FakeDevice(object):
        def __init__(self, name):
            self.name = name

    class FakeTrack(object):
        def __init__(self, device_names):
            self.devices = [FakeDevice(name) for name in device_names]

    for device_name, expected_map_name in (
        ("Drumazon 2", "Drumazon 2"),
        ("drumazon 2", "Drumazon 2"),
        ("Microtonic", "Microtonic"),
        ("MicrotonicMulti", "Microtonic"),
        ("MICROTONICMULTI", "Microtonic"),
    ):
        found_map = find_drum_map_for_track(FakeTrack(["EQ Eight", device_name]))
        assert found_map is not None and found_map.name == expected_map_name, device_name
    assert find_drum_map_for_track(FakeTrack(["Operator", "Drum Rack"])) is None
    assert find_drum_map_for_track(FakeTrack([])) is None

    drumazon_map = DRUM_MAP_REGISTRY[0]
    expected_drumazon = {
        "BD": (36, {35}), "RS": (37, set()), "SD": (38, {40}), "CP": (39, set()),
        "LT": (41, {43}), "CH": (42, {44}), "MT": (45, {47}), "OH": (46, set()),
        "HT": (48, {50}), "CR": (49, set()), "RD": (51, set()),
    }
    assert [voice.name for voice in drumazon_map.voices] == list(expected_drumazon)
    for voice in drumazon_map.voices:
        note, also_matches = expected_drumazon[voice.name]
        assert voice.note == note and set(voice.also_matches) == also_matches, voice
    assert drumazon_map.voice_at_pad_index(11) is None

    microtonic_map = DRUM_MAP_REGISTRY[1]
    assert [voice.note for voice in microtonic_map.voices] == list(range(36, 44))
    assert microtonic_map.voices[0].name == "Ch1"

    for bad_voices in ((), tuple(Voice("V{0}".format(i), 36 + i) for i in range(17)),
                       (Voice("A", 36), Voice("B", 37, also_matches=(36,)))):
        try:
            DrumMap("bad", ("bad",), bad_voices)
        except ValueError:
            pass
        else:
            raise AssertionError("expected loud failure for {0!r}".format(bad_voices))
    print("drum_maps self-check passed (o^^)o Drumazon 2 + Microtonic(Multi) resolve, lanes disjoint.")


if __name__ == "__main__":
    _self_check()
