# -*- coding: utf-8 -*-
"""Every RGB colour the script shows, grouped by page. Values are 0..127 per channel.

PURE PYTHON (no Live import). Self-check: `uv run python palette.py`.

Rules (plan section 5, docs/overview.md):
  - each page has a signature colour, shown on its page button and on the logo;
  - colours do not repeat within a page, so a pad that changes meaning under a hold
    (super, Length, Resolution, a held step) always changes colour.
The only colours not listed here are Live's own clip colours on the session page, which are
converted by rgb_from_live_color().
"""

from __future__ import absolute_import, print_function, unicode_literals

OFF = (0, 0, 0)


def scaled(rgb_triplet, numerator, denominator):
    """Scale brightness by numerator/denominator (integer maths, stays in 0..127)."""
    return tuple(channel * numerator // denominator for channel in rgb_triplet)


def quarter_brightness(rgb_triplet):
    return scaled(rgb_triplet, 1, 4)


# ---- global (page buttons, super, logo) -------------------------------------------------

SUPER_AT_REST = (20, 20, 20)
SUPER_HELD = (127, 127, 127)

SESSION_PAGE_SIGNATURE = (0, 127, 0)
DRUM_PAGE_SIGNATURE = (127, 60, 0)
SNAPSHOT_PAGE_SIGNATURE = (0, 40, 127)

PAGE_SIGNATURE_BY_PAGE_NAME = {
    "session": SESSION_PAGE_SIGNATURE,
    "drums": DRUM_PAGE_SIGNATURE,
    "snapshots": SNAPSHOT_PAGE_SIGNATURE,
}


def page_button_colour(page_name, is_selected):
    signature = PAGE_SIGNATURE_BY_PAGE_NAME[page_name]
    return signature if is_selected else quarter_brightness(signature)


# ---- session page -----------------------------------------------------------------------

SESSION_CLIP_RECORDING = (100, 0, 0)          # pulses
SESSION_EMPTY_SLOT_ON_ARMED_TRACK = (30, 0, 0)
SESSION_SCENE_HAS_CLIPS = (0, 45, 0)
SESSION_SCENE_TRIGGERED = (0, 110, 0)         # flashes
SESSION_ARROW_CAN_MOVE = (0, 30, 0)
SESSION_SUPER_STOP_TARGET = (127, 0, 0)       # super held: columns with a playing clip, scenes

SESSION_PAGE_COLOURS = {
    "clip_recording": SESSION_CLIP_RECORDING,
    "empty_slot_on_armed_track": SESSION_EMPTY_SLOT_ON_ARMED_TRACK,
    "scene_has_clips": SESSION_SCENE_HAS_CLIPS,
    "scene_triggered": SESSION_SCENE_TRIGGERED,
    "arrow_can_move": SESSION_ARROW_CAN_MOVE,
    "super_stop_target": SESSION_SUPER_STOP_TARGET,
}

LIVE_COLOR_CHANNEL_MAX = 255


def rgb_from_live_color(live_color_24_bit):
    """Live's clip.color (0xRRGGBB, 8 bits per channel) -> LPX RGB (7 bits per channel)."""
    if not isinstance(live_color_24_bit, int) or isinstance(live_color_24_bit, bool):
        raise TypeError("Live colour must be an int, got {0!r}".format(live_color_24_bit))
    if not (0 <= live_color_24_bit <= 0xFFFFFF):
        raise ValueError("Live colour {0!r} is not a 24-bit RGB value".format(live_color_24_bit))
    red = (live_color_24_bit >> 16) & 0xFF
    green = (live_color_24_bit >> 8) & 0xFF
    blue = live_color_24_bit & 0xFF
    return (red >> 1, green >> 1, blue >> 1)


# Animation styles, applied in one place (session_page's animation timer calls this).
ANIMATION_STATIC = "static"
ANIMATION_PULSE = "pulse"   # alternates full and quarter brightness
ANIMATION_FLASH = "flash"   # alternates full and off


def animated_colour(base_rgb, animation_style, is_bright_phase):
    if animation_style == ANIMATION_STATIC or is_bright_phase:
        return base_rgb
    if animation_style == ANIMATION_PULSE:
        return quarter_brightness(base_rgb)
    if animation_style == ANIMATION_FLASH:
        return OFF
    raise ValueError("unknown animation style {0!r}".format(animation_style))


# ---- drum page --------------------------------------------------------------------------

DRUM_STEP_EMPTY_INSIDE_LOOP = (6, 6, 6)
# Filled steps: amber ramp in 4 velocity bands, quietest first.
DRUM_STEP_FILLED_BY_VELOCITY_BAND = (
    (40, 18, 0),
    (69, 32, 0),
    (98, 46, 0),
    (127, 60, 0),
)
DRUM_PLAYHEAD = (127, 127, 127)
DRUM_FILLED_STEP_UNDER_PLAYHEAD = (127, 110, 90)

DRUM_VOICE_AVAILABLE = (0, 30, 40)
DRUM_VOICE_SELECTED = (0, 90, 120)
DRUM_NO_MATCHING_DRUM_MAP = (40, 0, 0)

DRUM_PATTERN_EMPTY = (20, 0, 25)
DRUM_PATTERN_HAS_CLIP = (50, 0, 70)
DRUM_PATTERN_SELECTED = (110, 0, 127)

# Velocity column: pink ramp, dim at rest, bright while a step is held. The current level
# (default velocity at rest, the held step's velocity while held) gets its own mark.
DRUM_VELOCITY_HELD_RAMP_LOW_TO_HIGH = (
    (16, 0, 8), (32, 0, 12), (48, 0, 16), (64, 0, 20),
    (80, 0, 24), (96, 0, 28), (112, 0, 32), (127, 0, 36),
)
DRUM_VELOCITY_REST_RAMP_LOW_TO_HIGH = tuple(
    quarter_brightness(colour) for colour in DRUM_VELOCITY_HELD_RAMP_LOW_TO_HIGH
)
DRUM_VELOCITY_REST_CURRENT_LEVEL = (40, 18, 28)
DRUM_VELOCITY_HELD_CURRENT_LEVEL = (127, 60, 90)

# Length overlay (hold up arrow): yellow.
DRUM_LENGTH_INSIDE_LOOP = (60, 60, 0)
DRUM_LENGTH_OUTSIDE_LOOP = (10, 10, 0)
DRUM_LENGTH_LOOP_END = (127, 127, 0)
DRUM_LENGTH_BUTTON_AT_REST = (20, 20, 0)
DRUM_LENGTH_BUTTON_HELD = (100, 100, 0)

# Resolution overlay (hold down arrow): teal.
DRUM_RESOLUTION_OPTION = (0, 50, 50)
DRUM_RESOLUTION_OPTION_SELECTED = (0, 127, 110)
DRUM_RESOLUTION_BUTTON_AT_REST = (0, 20, 20)
DRUM_RESOLUTION_BUTTON_HELD = (0, 100, 90)

DRUM_NUDGE_BUTTON = (30, 14, 0)

# Super held.
DRUM_SUPER_PATTERN_PASTE_TARGET = (90, 90, 90)
DRUM_SUPER_VOICE_CLEAR = (127, 0, 0)


def drum_velocity_band_index(velocity):
    """Velocity 1..127 -> band 0..3."""
    if not (1 <= velocity <= 127):
        raise ValueError("velocity {0!r} out of 1..127".format(velocity))
    return (int(velocity) - 1) * len(DRUM_STEP_FILLED_BY_VELOCITY_BAND) // 127


DRUM_PAGE_COLOURS = {
    "step_empty_inside_loop": DRUM_STEP_EMPTY_INSIDE_LOOP,
    "playhead": DRUM_PLAYHEAD,
    "filled_step_under_playhead": DRUM_FILLED_STEP_UNDER_PLAYHEAD,
    "voice_available": DRUM_VOICE_AVAILABLE,
    "voice_selected": DRUM_VOICE_SELECTED,
    "no_matching_drum_map": DRUM_NO_MATCHING_DRUM_MAP,
    "pattern_empty": DRUM_PATTERN_EMPTY,
    "pattern_has_clip": DRUM_PATTERN_HAS_CLIP,
    "pattern_selected": DRUM_PATTERN_SELECTED,
    "velocity_rest_current_level": DRUM_VELOCITY_REST_CURRENT_LEVEL,
    "velocity_held_current_level": DRUM_VELOCITY_HELD_CURRENT_LEVEL,
    "length_inside_loop": DRUM_LENGTH_INSIDE_LOOP,
    "length_outside_loop": DRUM_LENGTH_OUTSIDE_LOOP,
    "length_loop_end": DRUM_LENGTH_LOOP_END,
    "length_button_at_rest": DRUM_LENGTH_BUTTON_AT_REST,
    "length_button_held": DRUM_LENGTH_BUTTON_HELD,
    "resolution_option": DRUM_RESOLUTION_OPTION,
    "resolution_option_selected": DRUM_RESOLUTION_OPTION_SELECTED,
    "resolution_button_at_rest": DRUM_RESOLUTION_BUTTON_AT_REST,
    "resolution_button_held": DRUM_RESOLUTION_BUTTON_HELD,
    "nudge_button": DRUM_NUDGE_BUTTON,
    "super_pattern_paste_target": DRUM_SUPER_PATTERN_PASTE_TARGET,
    "super_voice_clear": DRUM_SUPER_VOICE_CLEAR,
}
for _band_index, _band_colour in enumerate(DRUM_STEP_FILLED_BY_VELOCITY_BAND):
    DRUM_PAGE_COLOURS["step_filled_band_{0}".format(_band_index)] = _band_colour
for _level_index in range(len(DRUM_VELOCITY_HELD_RAMP_LOW_TO_HIGH)):
    DRUM_PAGE_COLOURS["velocity_held_ramp_{0}".format(_level_index)] = (
        DRUM_VELOCITY_HELD_RAMP_LOW_TO_HIGH[_level_index])
    DRUM_PAGE_COLOURS["velocity_rest_ramp_{0}".format(_level_index)] = (
        DRUM_VELOCITY_REST_RAMP_LOW_TO_HIGH[_level_index])

# ---- snapshot page ----------------------------------------------------------------------

SNAPSHOT_ROW_HUES_TOP_TO_BOTTOM = (
    (127, 0, 0),     # red
    (127, 40, 0),    # orange
    (127, 110, 0),   # yellow
    (0, 127, 0),     # green
    (0, 127, 127),   # cyan
    (0, 0, 127),     # blue
    (70, 0, 127),    # purple
    (127, 0, 70),    # pink
)
SNAPSHOT_SUPER_EMPTY_SLOT = (20, 20, 20)
SNAPSHOT_SUPER_STORED_SLOT = (127, 127, 127)


def snapshot_stored_colour(row_index_from_top):
    return quarter_brightness(SNAPSHOT_ROW_HUES_TOP_TO_BOTTOM[row_index_from_top])


def snapshot_active_colour(row_index_from_top):
    return SNAPSHOT_ROW_HUES_TOP_TO_BOTTOM[row_index_from_top]


SNAPSHOT_PAGE_COLOURS = {
    "super_empty_slot": SNAPSHOT_SUPER_EMPTY_SLOT,
    "super_stored_slot": SNAPSHOT_SUPER_STORED_SLOT,
}
for _row_index in range(len(SNAPSHOT_ROW_HUES_TOP_TO_BOTTOM)):
    SNAPSHOT_PAGE_COLOURS["row_{0}_active".format(_row_index)] = snapshot_active_colour(_row_index)
    SNAPSHOT_PAGE_COLOURS["row_{0}_stored".format(_row_index)] = snapshot_stored_colour(_row_index)


def _assert_no_repeated_colour(page_name, named_colours):
    names_by_colour = {}
    for name, colour in named_colours.items():
        assert colour != OFF, (page_name, name, "OFF is implicit, never a named state")
        assert all(isinstance(c, int) and 0 <= c <= 127 for c in colour), (page_name, name, colour)
        names_by_colour.setdefault(colour, []).append(name)
    repeated = {colour: names for colour, names in names_by_colour.items() if len(names) > 1}
    assert not repeated, (page_name, "colour reused within a page", repeated)


def _self_check():
    _assert_no_repeated_colour("session", SESSION_PAGE_COLOURS)
    _assert_no_repeated_colour("drums", DRUM_PAGE_COLOURS)
    _assert_no_repeated_colour("snapshots", SNAPSHOT_PAGE_COLOURS)
    global_colours = {"super_at_rest": SUPER_AT_REST, "super_held": SUPER_HELD}
    for page_name in PAGE_SIGNATURE_BY_PAGE_NAME:
        global_colours[page_name + "_selected"] = page_button_colour(page_name, True)
        global_colours[page_name + "_unselected"] = page_button_colour(page_name, False)
    _assert_no_repeated_colour("global", global_colours)

    assert rgb_from_live_color(0xFF8000) == (127, 64, 0)
    assert rgb_from_live_color(0x000000) == (0, 0, 0)
    for bad in (None, -1, 0x1000000):
        try:
            rgb_from_live_color(bad)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("expected loud failure for {0!r}".format(bad))

    assert animated_colour((100, 40, 8), ANIMATION_PULSE, False) == (25, 10, 2)
    assert animated_colour((100, 40, 8), ANIMATION_FLASH, False) == OFF
    assert animated_colour((100, 40, 8), ANIMATION_STATIC, False) == (100, 40, 8)
    assert animated_colour((100, 40, 8), ANIMATION_FLASH, True) == (100, 40, 8)

    assert [drum_velocity_band_index(v) for v in (1, 31, 32, 64, 96, 127)] == [0, 0, 0, 1, 2, 3]
    print("palette self-check passed \\(^o^)/ no colour repeats within any page.")


if __name__ == "__main__":
    _self_check()
