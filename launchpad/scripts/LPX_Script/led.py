# -*- coding: utf-8 -*-
"""The one LED system: Launchpad X batch-RGB SysEx and a generic LedPainter.

PURE PYTHON (no Live import). Self-check: `uv run python led.py`.

Batch RGB (Programmer's Reference, lighting section; knowledge_base/hardware/
novation_launchpad_x/notes.md):  F0 00 20 29 02 0C 03 <spec> <spec> ... F7
Each spec for RGB is `03 <index> <r> <g> <b>`, r/g/b 0..127, index = the pad's note/CC.
At most 81 specs per message, so longer lists are split into several messages.

Every page paints through LedPainter.paint(); no other code writes LEDs (the framework's
Skin / palette-index path is not used).
"""

from __future__ import absolute_import, print_function, unicode_literals

# Package import inside Live, plain import for the standalone self-check.
try:
    from . import layout
except ImportError:
    import layout

LPX_LED_BATCH_COMMAND_BYTE = 0x03
LPX_LED_SPEC_TYPE_RGB = 3
LPX_MAX_LED_SPECS_PER_MESSAGE = 81
LED_COLOUR_BYTE_MAX = 127


def _validated_colour_byte(value):
    """Colour bytes must be ints in 0..127. Anything else is a bug upstream, so raise loudly."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("colour byte must be int, got {0!r}".format(value))
    if not (0 <= value <= LED_COLOUR_BYTE_MAX):
        raise ValueError("colour byte {0} out of 0..127".format(value))
    return value


def build_rgb_led_batch_sysex(led_index_and_rgb_pairs):
    """[(led_index, (r, g, b)), ...] -> list of complete SysEx tuples, chunked at 81."""
    led_specs = list(led_index_and_rgb_pairs)
    messages = []
    for chunk_start in range(0, len(led_specs), LPX_MAX_LED_SPECS_PER_MESSAGE):
        message_body = []
        for led_index, rgb_triplet in led_specs[chunk_start:chunk_start + LPX_MAX_LED_SPECS_PER_MESSAGE]:
            red_byte, green_byte, blue_byte = rgb_triplet
            message_body.extend((
                LPX_LED_SPEC_TYPE_RGB,
                led_index,
                _validated_colour_byte(red_byte),
                _validated_colour_byte(green_byte),
                _validated_colour_byte(blue_byte),
            ))
        messages.append(
            layout.LPX_SYSEX_HEADER
            + (LPX_LED_BATCH_COMMAND_BYTE,)
            + tuple(message_body)
            + (layout.LPX_SYSEX_END,)
        )
    return messages


class LedPainter(object):
    """Sends batch-RGB SysEx through an injected send function (the surface's _send_midi)."""

    def __init__(self, send_sysex_message):
        self._send_sysex_message = send_sysex_message

    def paint(self, led_index_and_rgb_pairs):
        for message in build_rgb_led_batch_sysex(led_index_and_rgb_pairs):
            self._send_sysex_message(message)


def _self_check():
    only_message = build_rgb_led_batch_sysex([(81, (127, 0, 0))])
    assert len(only_message) == 1
    message = only_message[0]
    assert message[:6] == layout.LPX_SYSEX_HEADER
    assert message[6:12] == (LPX_LED_BATCH_COMMAND_BYTE, LPX_LED_SPEC_TYPE_RGB, 81, 127, 0, 0)
    assert message[-1] == layout.LPX_SYSEX_END

    for bad_colour in ((128, 0, 0), (-1, 0, 0), (1.5, 0, 0)):
        try:
            build_rgb_led_batch_sysex([(11, bad_colour)])
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("expected loud failure for {0}".format(bad_colour))

    ninety_leds = [(11 + index, (1, 2, 3)) for index in range(90)]
    split_messages = build_rgb_led_batch_sysex(ninety_leds)
    assert len(split_messages) == 2
    spec_counts = [(len(m) - len(layout.LPX_SYSEX_HEADER) - 2) // 5 for m in split_messages]
    assert spec_counts == [81, 9], spec_counts

    # A full page clear (76 LEDs) fits in one message.
    clear_messages = build_rgb_led_batch_sysex(
        [(index, (0, 0, 0)) for index in layout.PAGE_OWNED_LED_INDICES]
    )
    assert len(clear_messages) == 1
    assert build_rgb_led_batch_sysex([]) == []

    sent_messages = []
    LedPainter(sent_messages.append).paint(ninety_leds)
    assert sent_messages == split_messages
    print("led self-check passed (=^.^=) framing, loud range errors, 81-chunking OK.")


if __name__ == "__main__":
    _self_check()
