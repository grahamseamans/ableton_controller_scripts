# -*- coding: utf-8 -*-
"""Mixer snapshots: format, capture, apply, matching and persistence inside the Live set.

PURE PYTHON, duck-typed against Live's Song/Track objects (no Live import).
Self-check against fake song objects: `uv run python snapshot_store.py`.

Stored as song.set_data(SNAPSHOT_DATA_KEY, <JSON string>):

  {"format": 1,
   "slots": {"81": {"tracks":  [{"name": "Kick", "volume": 0.85}, ...],
                    "returns": [{"name": "A-Reverb", "volume": 0.70}, ...]}}}

  - slot keys are grid note numbers (strings, JSON object keys);
  - volume = track.mixer_device.volume.value;
  - tracks follow song.tracks order (groups included); returns follow song.return_tracks;
    master is not stored.
Recall matches by name; duplicate names match in the order they occur. Tracks missing from
the set are skipped; tracks not in the snapshot are left alone.
Saving re-reads the stored data, merges one slot and writes it back (read-modify-write), so a
second Launchpad writing the same key does not lose the other's slots.
"""

from __future__ import absolute_import, print_function, unicode_literals

import json

SNAPSHOT_DATA_KEY = "lpx_script.mixer_snapshots"
SNAPSHOT_FORMAT_VERSION = 1
VOLUME_CHANGE_TOLERANCE = 1e-4


class SnapshotStoreError(Exception):
    """Stored data that is not a snapshot store we understand. Never silently discarded."""


def empty_store():
    return {"format": SNAPSHOT_FORMAT_VERSION, "slots": {}}


def parse_store(stored_value):
    """song.get_data value -> store dict. None / "" (nothing stored yet) -> empty store."""
    if stored_value is None or stored_value == "":
        return empty_store()
    try:
        store = json.loads(stored_value)
    except (TypeError, ValueError) as parse_error:
        raise SnapshotStoreError("{0!r} is not valid JSON: {1}".format(SNAPSHOT_DATA_KEY, parse_error))
    if not isinstance(store, dict) or store.get("format") != SNAPSHOT_FORMAT_VERSION:
        raise SnapshotStoreError("{0!r} has unknown format: {1!r}".format(
            SNAPSHOT_DATA_KEY, store.get("format") if isinstance(store, dict) else store))
    if not isinstance(store.get("slots"), dict):
        raise SnapshotStoreError("{0!r} has no 'slots' object".format(SNAPSHOT_DATA_KEY))
    return store


def load_store(song):
    return parse_store(song.get_data(SNAPSHOT_DATA_KEY, None))


def slot_key_for_grid_note(grid_note):
    return str(int(grid_note))


def _capture_track_list(live_tracks):
    return [
        {"name": live_track.name, "volume": float(live_track.mixer_device.volume.value)}
        for live_track in live_tracks
    ]


def capture_snapshot(song):
    return {
        "tracks": _capture_track_list(song.tracks),
        "returns": _capture_track_list(song.return_tracks),
    }


def save_snapshot_to_slot(song, slot_key, snapshot):
    """Read-modify-write: merge one slot into what is stored now. Overwriting is allowed.
    Returns the store as written."""
    store = load_store(song)
    store["slots"][slot_key] = snapshot
    song.set_data(SNAPSHOT_DATA_KEY, json.dumps(store, sort_keys=True))
    return store


def pair_entries_with_live_tracks(snapshot_entries, live_tracks):
    """[(entry, live_track)] matched by name; the k-th entry named X pairs with the k-th live
    track named X. Entries with no live partner are returned separately as unmatched."""
    live_tracks_by_name = {}
    for live_track in live_tracks:
        live_tracks_by_name.setdefault(live_track.name, []).append(live_track)
    occurrence_count_by_name = {}
    matched_pairs = []
    unmatched_entries = []
    for entry in snapshot_entries:
        occurrence_index = occurrence_count_by_name.get(entry["name"], 0)
        occurrence_count_by_name[entry["name"]] = occurrence_index + 1
        candidates = live_tracks_by_name.get(entry["name"], [])
        if occurrence_index < len(candidates):
            matched_pairs.append((entry, candidates[occurrence_index]))
        else:
            unmatched_entries.append(entry)
    return matched_pairs, unmatched_entries


def _all_pairs(song, snapshot):
    track_pairs, unmatched_tracks = pair_entries_with_live_tracks(snapshot["tracks"], song.tracks)
    return_pairs, unmatched_returns = pair_entries_with_live_tracks(snapshot["returns"], song.return_tracks)
    return track_pairs + return_pairs, unmatched_tracks + unmatched_returns


def apply_snapshot(song, snapshot):
    """Set every matched track's volume. Returns the entries that had no track in the set
    (the caller logs them)."""
    matched_pairs, unmatched_entries = _all_pairs(song, snapshot)
    for entry, live_track in matched_pairs:
        live_track.mixer_device.volume.value = entry["volume"]
    return unmatched_entries


def song_still_matches_snapshot(song, snapshot, tolerance=VOLUME_CHANGE_TOLERANCE):
    """False as soon as any matched track's volume differs from the snapshot by > tolerance."""
    matched_pairs, _unmatched_entries = _all_pairs(song, snapshot)
    for entry, live_track in matched_pairs:
        if abs(live_track.mixer_device.volume.value - entry["volume"]) > tolerance:
            return False
    return True


def _self_check():

    class FakeParameter(object):
        def __init__(self, value):
            self.value = value

    class FakeMixerDevice(object):
        def __init__(self, volume):
            self.volume = FakeParameter(volume)

    class FakeTrack(object):
        def __init__(self, name, volume):
            self.name = name
            self.mixer_device = FakeMixerDevice(volume)

    class FakeSong(object):
        def __init__(self, tracks, return_tracks):
            self.tracks = tracks
            self.return_tracks = return_tracks
            self.master_track = FakeTrack("Master", 0.5)
            self._data = {}

        def get_data(self, key, default):
            return self._data.get(key, default)

        def set_data(self, key, value):
            assert isinstance(value, str)
            self._data[key] = value

    song = FakeSong(
        [FakeTrack("Kick", 0.85), FakeTrack("Hat", 0.5), FakeTrack("Hat", 0.4), FakeTrack("Drums", 0.7)],
        [FakeTrack("A-Reverb", 0.7)],
    )
    assert load_store(song) == empty_store()

    snapshot = capture_snapshot(song)
    assert [entry["name"] for entry in snapshot["tracks"]] == ["Kick", "Hat", "Hat", "Drums"]
    assert snapshot["returns"] == [{"name": "A-Reverb", "volume": 0.7}]
    assert "Master" not in json.dumps(snapshot)

    save_snapshot_to_slot(song, slot_key_for_grid_note(81), snapshot)
    stored = json.loads(song.get_data(SNAPSHOT_DATA_KEY, None))
    assert stored["format"] == 1 and list(stored["slots"]) == ["81"]

    # Read-modify-write: another instance's slot survives our save.
    other_instance_store = load_store(song)
    other_instance_store["slots"]["11"] = {"tracks": [], "returns": []}
    song.set_data(SNAPSHOT_DATA_KEY, json.dumps(other_instance_store))
    save_snapshot_to_slot(song, "82", snapshot)
    assert sorted(load_store(song)["slots"]) == ["11", "81", "82"]

    # Change the mixer, then recall: duplicates match in order, master untouched.
    assert song_still_matches_snapshot(song, snapshot)
    song.tracks[2].mixer_device.volume.value = 0.1
    song.return_tracks[0].mixer_device.volume.value = 0.2
    song.master_track.mixer_device.volume.value = 0.9
    assert not song_still_matches_snapshot(song, snapshot)
    song.tracks[2].mixer_device.volume.value = 0.4 + VOLUME_CHANGE_TOLERANCE / 2
    song.return_tracks[0].mixer_device.volume.value = 0.7
    assert song_still_matches_snapshot(song, snapshot)
    song.tracks[2].mixer_device.volume.value = 0.1
    unmatched = apply_snapshot(song, load_store(song)["slots"]["81"])
    assert unmatched == []
    assert [t.mixer_device.volume.value for t in song.tracks] == [0.85, 0.5, 0.4, 0.7]
    assert song.master_track.mixer_device.volume.value == 0.9

    # A track missing from the set is skipped and reported; extra tracks are left alone.
    smaller_song = FakeSong([FakeTrack("Hat", 0.0), FakeTrack("Bass", 0.33)], [])
    unmatched = apply_snapshot(smaller_song, snapshot)
    assert [entry["name"] for entry in unmatched] == ["Kick", "Hat", "Drums", "A-Reverb"]
    assert smaller_song.tracks[0].mixer_device.volume.value == 0.5
    assert smaller_song.tracks[1].mixer_device.volume.value == 0.33

    # Garbage in the set is a loud error, never silently replaced.
    for garbage in ("not json", json.dumps({"format": 99, "slots": {}}), json.dumps([1, 2])):
        try:
            parse_store(garbage)
        except SnapshotStoreError:
            pass
        else:
            raise AssertionError("expected SnapshotStoreError for {0!r}".format(garbage))
    print("snapshot_store self-check passed (b^_^)b capture, merge, name matching, tolerance OK.")


if __name__ == "__main__":
    _self_check()
