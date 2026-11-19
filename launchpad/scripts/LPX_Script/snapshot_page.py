# -*- coding: utf-8 -*-
"""Snapshot page: 64 mixer-snapshot slots (launchpad/docs/mixer_snapshot.md).

  pad            -> recall the stored snapshot (track + return volumes, matched by name)
  super + pad    -> save the current mixer into that slot (overwrites)

LEDs: each row has its own hue. Stored slot = quarter brightness, the recalled snapshot while
the mixer still matches it = full brightness, empty = off. Super held: empty pads grey,
stored pads white. Right column and arrows are unused (dark).

The active mark is in memory only: a volume listener over every track and return clears it
as soon as any value differs from the active snapshot by more than 1e-4.
The store is read in the constructor and re-read on every page entry (repaint_page).
"""

from __future__ import absolute_import, print_function, unicode_literals

import logging

from ableton.v2.base import listens, listens_group
from ableton.v2.control_surface import Component

from . import layout
from . import palette
from . import snapshot_store

logger = logging.getLogger(__name__)


class SnapshotPageComponent(Component):

    def __init__(self, led_painter=None, global_controls=None, *a, **k):
        super(SnapshotPageComponent, self).__init__(*a, **k)
        if led_painter is None or global_controls is None:
            raise ValueError("SnapshotPageComponent needs led_painter and global_controls")
        self._led_painter = led_painter
        self._global_controls = global_controls
        self._store = snapshot_store.load_store(self.song)
        self._active_slot_key = None
        self._is_applying_snapshot = False

        self._on_super_held_changed.subject = global_controls
        self._on_tracks_changed.subject = self.song
        self._on_return_tracks_changed.subject = self.song
        self._rebind_volume_listeners()

    # ---- element setters (Layer) --------------------------------------------------------

    def set_snapshot_matrix(self, matrix):
        self._on_snapshot_matrix_value.subject = matrix

    # ---- input --------------------------------------------------------------------------

    @listens("value")
    def _on_snapshot_matrix_value(self, value, column_index, row_index, _is_momentary):
        if value <= 0:
            return
        slot_key = snapshot_store.slot_key_for_grid_note(
            layout.grid_note_for_matrix_position(column_index, row_index))
        if self._global_controls.super_held:
            self._save_slot(slot_key)
        else:
            self._recall_slot(slot_key)
        self._repaint_grid()

    def _save_slot(self, slot_key):
        snapshot = snapshot_store.capture_snapshot(self.song)
        self._store = snapshot_store.save_snapshot_to_slot(self.song, slot_key, snapshot)
        logger.info("LPX Script snapshots: saved slot %s (%d tracks, %d returns)",
                    slot_key, len(snapshot["tracks"]), len(snapshot["returns"]))

    def _recall_slot(self, slot_key):
        snapshot = self._store["slots"].get(slot_key)
        if snapshot is None:
            logger.info("LPX Script snapshots: slot %s is empty, nothing to recall", slot_key)
            return
        self._is_applying_snapshot = True
        try:
            unmatched_entries = snapshot_store.apply_snapshot(self.song, snapshot)
        finally:
            self._is_applying_snapshot = False
        if unmatched_entries:
            logger.warning("LPX Script snapshots: slot %s names not in this set, skipped: %s",
                           slot_key, ", ".join(entry["name"] for entry in unmatched_entries))
        self._active_slot_key = slot_key
        logger.info("LPX Script snapshots: recalled slot %s", slot_key)

    # ---- mixer listeners ----------------------------------------------------------------

    def _rebind_volume_listeners(self):
        all_mixer_tracks = list(self.song.tracks) + list(self.song.return_tracks)
        self._on_volume_value_changed.replace_subjects(
            [mixer_track.mixer_device.volume for mixer_track in all_mixer_tracks])

    @listens("tracks")
    def _on_tracks_changed(self):
        self._rebind_volume_listeners()
        self._check_active_snapshot_still_matches()

    @listens("return_tracks")
    def _on_return_tracks_changed(self):
        self._rebind_volume_listeners()
        self._check_active_snapshot_still_matches()

    @listens_group("value")
    def _on_volume_value_changed(self, _volume_parameter):
        if self._is_applying_snapshot:
            return  # our own recall is mid-way; the active mark is set when it finishes
        self._check_active_snapshot_still_matches()

    def _check_active_snapshot_still_matches(self):
        if self._active_slot_key is None:
            return
        active_snapshot = self._store["slots"][self._active_slot_key]
        if not snapshot_store.song_still_matches_snapshot(self.song, active_snapshot):
            logger.info("LPX Script snapshots: mixer moved, slot %s no longer active", self._active_slot_key)
            self._active_slot_key = None
            self._repaint_grid()

    @listens("super_held")
    def _on_super_held_changed(self, _is_held):
        self._repaint_grid()

    # ---- LEDs ---------------------------------------------------------------------------

    def _pad_colour(self, slot_key, row_index, super_held):
        is_stored = slot_key in self._store["slots"]
        if super_held:
            return palette.SNAPSHOT_SUPER_STORED_SLOT if is_stored else palette.SNAPSHOT_SUPER_EMPTY_SLOT
        if not is_stored:
            return palette.OFF
        if slot_key == self._active_slot_key:
            return palette.snapshot_active_colour(row_index)
        return palette.snapshot_stored_colour(row_index)

    def _repaint_grid(self):
        if not self.is_enabled():
            return  # a disabled page never paints; repaint_page() runs on entry
        super_held = self._global_controls.super_held
        leds = []
        for row_index in range(layout.GRID_SIDE_LENGTH_IN_PADS):
            for column_index in range(layout.GRID_SIDE_LENGTH_IN_PADS):
                grid_note = layout.grid_note_for_matrix_position(column_index, row_index)
                leds.append((grid_note, self._pad_colour(
                    snapshot_store.slot_key_for_grid_note(grid_note), row_index, super_held)))
        self._led_painter.paint(leds)

    def repaint_page(self):
        """Page entry: re-read the store (another Launchpad may have saved), then paint."""
        self._store = snapshot_store.load_store(self.song)
        self._check_active_snapshot_still_matches()
        self._repaint_grid()
