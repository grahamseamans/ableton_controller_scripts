# -*- coding: utf-8 -*-
"""Jomox AlphaBase channel-16 keymap: the single source of truth for note <-> instrument.

PURE PYTHON. This module MUST NOT import Live / ableton so it can be unit-tested outside
Ableton (run `uv run python alphabase_map.py` to execute the self-check at the bottom).

The AlphaBase, on MIDI channel 16, maps every instrument to 4 consecutive notes = 4 tunings
(pitch deltas 0 / 6 / 12 / 18 semitones). See AlphaBase manual section 13.1.1 and the
project's ARCHITECTURE/midi_mappings.md (section C) for the canonical table this encodes.

Canonical formula:  note = ALPHABASE_KEYMAP_BASE_NOTE + instrument_index * 4 + tuning
where instrument_index in 0..10 and tuning in 0..3.
"""

from __future__ import absolute_import, print_function, unicode_literals

# The keymap starts at MIDI note 36 (C1) for Kick / tuning 0.
ALPHABASE_KEYMAP_BASE_NOTE = 36

# Number of distinct tunings each instrument exposes on channel 16.
ALPHABASE_TUNINGS_PER_INSTRUMENT = 4

# The semitone pitch delta produced by each tuning index (manual section 13.1.1).
# This is informational for UI/labelling; the AlphaBase applies it internally from the note.
ALPHABASE_TUNING_SEMITONE_DELTAS = (0, 6, 12, 18)

# The 11 instruments in keymap order. Index == instrument_index in the note formula.
# Names taken verbatim from ARCHITECTURE/midi_mappings.md (section C).
ALPHABASE_INSTRUMENT_NAMES = (
    "Kick",       # 0  -> notes 36..39
    "Snare",      # 1  -> notes 40..43
    "Closed HH",  # 2  -> notes 44..47
    "Open HH",    # 3  -> notes 48..51
    "Clap",       # 4  -> notes 52..55
    "Rim",        # 5  -> notes 56..59
    "Crash",      # 6  -> notes 60..63
    "Ride",       # 7  -> notes 64..67
    "X1 sample",  # 8  -> notes 68..71
    "X2 sample",  # 9  -> notes 72..75
    "FM synth",   # 10 -> notes 76..79
)

ALPHABASE_INSTRUMENT_COUNT = len(ALPHABASE_INSTRUMENT_NAMES)

# The AlphaBase keymap-mode notes live on this MIDI channel (1-based, as humans say it).
# Live's "MIDI To ... Ch. 16" re-channelizes the whole track to this channel.
ALPHABASE_KEYMAP_MIDI_CHANNEL_ONE_BASED = 16
# Same channel, zero-based, for code that builds raw MIDI status bytes.
ALPHABASE_KEYMAP_MIDI_CHANNEL_ZERO_BASED = ALPHABASE_KEYMAP_MIDI_CHANNEL_ONE_BASED - 1

# Lowest and highest notes the keymap occupies, inclusive (derived, not hand-typed).
ALPHABASE_KEYMAP_LOWEST_NOTE = ALPHABASE_KEYMAP_BASE_NOTE
ALPHABASE_KEYMAP_HIGHEST_NOTE = (
    ALPHABASE_KEYMAP_BASE_NOTE
    + ALPHABASE_INSTRUMENT_COUNT * ALPHABASE_TUNINGS_PER_INSTRUMENT
    - 1
)


def note_for_instrument_and_tuning(instrument_index, tuning_index):
    """Return the channel-16 MIDI note for the given instrument and tuning.

    Raises ValueError on out-of-range input rather than silently clamping, because a bad
    index here means a bug in a caller's region->index math, and we never want to invent a
    note for the wrong drum.
    """
    if not (0 <= instrument_index < ALPHABASE_INSTRUMENT_COUNT):
        raise ValueError(
            "instrument_index {0} out of range 0..{1}".format(
                instrument_index, ALPHABASE_INSTRUMENT_COUNT - 1
            )
        )
    if not (0 <= tuning_index < ALPHABASE_TUNINGS_PER_INSTRUMENT):
        raise ValueError(
            "tuning_index {0} out of range 0..{1}".format(
                tuning_index, ALPHABASE_TUNINGS_PER_INSTRUMENT - 1
            )
        )
    return (
        ALPHABASE_KEYMAP_BASE_NOTE
        + instrument_index * ALPHABASE_TUNINGS_PER_INSTRUMENT
        + tuning_index
    )


def instrument_and_tuning_for_note(midi_note):
    """Reverse of note_for_instrument_and_tuning: (instrument_index, tuning_index).

    Returns None when the note is outside the keymap range (e.g. a stray note recorded by
    other gear) so callers can explicitly ignore it instead of mis-attributing it to a drum.
    """
    if not (ALPHABASE_KEYMAP_LOWEST_NOTE <= midi_note <= ALPHABASE_KEYMAP_HIGHEST_NOTE):
        return None
    offset_from_base = midi_note - ALPHABASE_KEYMAP_BASE_NOTE
    instrument_index = offset_from_base // ALPHABASE_TUNINGS_PER_INSTRUMENT
    tuning_index = offset_from_base % ALPHABASE_TUNINGS_PER_INSTRUMENT
    return (instrument_index, tuning_index)


def instrument_name(instrument_index):
    """Human-readable name for an instrument index (for Live status messages / labelling)."""
    if not (0 <= instrument_index < ALPHABASE_INSTRUMENT_COUNT):
        raise ValueError(
            "instrument_index {0} out of range 0..{1}".format(
                instrument_index, ALPHABASE_INSTRUMENT_COUNT - 1
            )
        )
    return ALPHABASE_INSTRUMENT_NAMES[instrument_index]


def _self_check():
    """Assert the encoded table matches the canonical table in midi_mappings.md (section C)."""
    expected_first_note_per_instrument = {
        "Kick": 36,
        "Snare": 40,
        "Closed HH": 44,
        "Open HH": 48,
        "Clap": 52,
        "Rim": 56,
        "Crash": 60,
        "Ride": 64,
        "X1 sample": 68,
        "X2 sample": 72,
        "FM synth": 76,
    }
    assert ALPHABASE_INSTRUMENT_COUNT == 11, ALPHABASE_INSTRUMENT_COUNT

    # Every instrument's tuning-0 note must match the published table.
    for instrument_index, name in enumerate(ALPHABASE_INSTRUMENT_NAMES):
        assert name in expected_first_note_per_instrument, name
        produced = note_for_instrument_and_tuning(instrument_index, 0)
        assert produced == expected_first_note_per_instrument[name], (
            name, produced, expected_first_note_per_instrument[name]
        )

    # Full forward/reverse round trip across the whole keymap.
    for instrument_index in range(ALPHABASE_INSTRUMENT_COUNT):
        for tuning_index in range(ALPHABASE_TUNINGS_PER_INSTRUMENT):
            note = note_for_instrument_and_tuning(instrument_index, tuning_index)
            assert instrument_and_tuning_for_note(note) == (instrument_index, tuning_index), note

    # Keymap spans exactly notes 36..79.
    assert ALPHABASE_KEYMAP_LOWEST_NOTE == 36, ALPHABASE_KEYMAP_LOWEST_NOTE
    assert ALPHABASE_KEYMAP_HIGHEST_NOTE == 79, ALPHABASE_KEYMAP_HIGHEST_NOTE

    # Notes just outside the range reverse-map to None (never invented).
    assert instrument_and_tuning_for_note(35) is None
    assert instrument_and_tuning_for_note(80) is None

    # Out-of-range forward calls raise rather than fabricate.
    for bad in (-1, ALPHABASE_INSTRUMENT_COUNT):
        try:
            note_for_instrument_and_tuning(bad, 0)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for instrument_index {0}".format(bad))

    print("alphabase_map self-check passed: 11 instruments, notes 36..79, round-trip OK.")


if __name__ == "__main__":
    _self_check()
