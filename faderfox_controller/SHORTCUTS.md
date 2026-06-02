# Shortcuts

Things that were intentionally hacky, simplified, or left for later. Track
here so we can come back to them.

## Unverified Live API strings (need a Live console pass)

The PC12 script identifies devices and parameters by string match. These were
best-guesses; verify on the user's Live install (Live's Python console is the
fastest way: print `track.devices[*].class_name` and `device.parameters[*].name`).

- `track_device_finder.py` — `COMPRESSOR_CLASS_NAME = "Compressor2"`. May be
  `"Compressor"` on newer Live.
- `page_compression.py` — Compressor parameter names: `"Threshold"`,
  `"Ratio"`, `"Attack"`, `"Release"`, `"Knee"`, `"Output Gain"`.
- `page_eq.py` and `page_performance.py` — EQ Eight band parameter names use
  the pattern `"<n> Frequency A"` and `"<n> Gain A"`. Some Live versions may
  use just `"<n> Frequency"` / `"<n> Gain"` (no `A` chain suffix) or different
  spelling.

If any name is wrong, the affected control silently no-ops — no error. So the
test pattern is: wiggle a control, check Live's parameter; if nothing moves,
re-verify the name string.

## MX12 encoder = absolute, not relative

`mx12_surface.py` uses `Live.MidiMap.MapMode.absolute` for the scene-select
encoder. With detented encoders this can feel jumpy when many scenes exist
(each tick scales by `127/scene_count`). If it feels wrong, switch to
`Live.MidiMap.MapMode.relative_smooth_two_compliment` and rewrite
`_on_scene_select_encoder_value` to step relative to current scene index.

The PC12 encoder turn is also flagged in `pc12_cc_layout.py` (`PC12_ENCODER_TURN_CC = 85`)
but currently unbound; not yet a problem.

## Linear MIDI-value → parameter-value mapping in the PC12 direct-bind path

`_DirectParameterEncoderRowBinder` writes
`parameter.value = min + (midi_value/127) * (max - min)`. This is correct for
linear parameters (gain, ratio) but may feel uneven for parameters Live treats
as logarithmic in the UI (e.g. EQ band frequency). Cross-check during
testing — if frequency knob feel is bad, replace the linear formula with a
log mapping for those specific parameters.

## ~~`MixerComponent(num_returns=4, ...)` kwarg~~ — RESOLVED 2026-05-08

`num_returns` is not a valid kwarg in Live 12.4's `MixerComponent` — it cascaded
to `object.__init__` and crashed PC12 script load. Removed; Live infers the
send count from the shape of the `send_controls` Layer entry.
