# Faderfox Controller — Architecture

## Vision

Build a 12-channel mixing desk inside Ableton Live, controlled by an MX12 + PC12.
Each Live audio track corresponds to one labeled audio-interface input. The MX12
handles base mixing (volume / pan / solo / mute). The PC12 handles per-track
effects across three pages (Performance / Compression / EQ). The user switches
pages by switching the PC12's active setup.

## The one pattern: channel-routed CC binding

Both devices stay on **factory generic setups** — no onboard reprogramming.

Faderfox's factory generic setups (1–20, 23–29 on MX12; 1–20, 25–29 on PC12) all
emit **the same CC layout**, only the MIDI channel changes per setup. The manual
gives this for free: setup 1 → channel 1, setup 2 → channel 2, …, setup 16 →
channel 16.

This means the device's own setup-switching mechanism IS our page-switching
mechanism. From the script's point of view the contract is dead simple:

> `(midi_channel, cc_number) → live_parameter`

The script has no mode state, no modifier keys, no chord buttons. When the user
switches setup on the PC12, MIDI starts arriving on a different channel; the
script routes it to a different parameter. That's the entire mechanism.

## Why this pattern won

We iterated through several worse approaches first. See `history.md` for what
was tried, why it failed, and how we landed here.

The short version: this is the pattern Faderfox already designed for. The
on-device setups + factory channel-per-setup convention give us free page
switching with no reprogramming and no script-side mode tracking. Anything
else fights the hardware.

## Devices and setups

### MX12 — one setup, one layer of meaning
- **Setup 1** (channel 1)
- Single layout: mixing surface

### PC12 — three setups, three pages
- **Setup 1** (channel 1) = Performance
- **Setup 2** (channel 2) = EQ
- **Setup 3** (channel 3) = Compression

User switches pages via PC12 setup mode: hold red shift + double-tap blue →
turn encoder to 1/2/3 → hold red shift + tap blue once to exit.

## Required Live devices per track

Each of the 12 audio tracks must contain three devices, in this order in the
chain:

1. **Tonal EQ Eight** — used by the EQ page
2. **Compressor** — used by the Compression page
3. **Filter EQ Eight** — used by the Performance page for HP/LP filter sweeps

The script identifies the two EQ Eights by **position**: the first `Eq8` it
finds on the track is the tonal one; the second `Eq8` is the filter one. No
device renaming required, but the chain order does need to be tonal-EQ →
compressor → filter-EQ.

### Tonal EQ Eight band convention

The user manually configures band types on each track's tonal EQ Eight as:

| Band | Filter type | EQ-page row(s) controlling it |
|------|-------------|-------------------------------|
| 1    | Low shelf   | Row A (gain), Row B (freq)    |
| 2    | Bell (peaking) | Row C (gain), Row D (freq) |
| 3    | High shelf  | Row E (gain), Row F (freq)    |
| 4–8  | (free)      | —                             |

### Filter EQ Eight band convention

| Band | Filter type | Performance-page row controlling it |
|------|-------------|-------------------------------------|
| 1    | High pass   | Row E (freq)                        |
| 2    | Low pass    | Row F (freq)                        |
| 3–8  | (free)      | —                                   |

### Behavior when devices are missing

If a track is missing one of the three devices, the controls that need it
silently no-op for that track (no errors, no fallbacks — just nothing happens
for that specific control). The other tracks and other controls are unaffected.

This is intentional: it matches the "no quiet fallbacks" rule by being
explicit (parameter is unbound when device is missing) rather than having the
script invent fake parameters or silently substitute something else.

## CC ↔ parameter mappings

The full per-channel CC mapping table lives in `midi_mappings.md`. That file is
the contract between device and script and is the source of truth.

## File structure (when implemented)

```
scripts/
  Faderfox_MX12_Mixer/
    __init__.py
    mx12_surface.py         # ControlSurface; builds elements; binds layer
    mx12_cc_layout.py       # CC constants for MX12 setup 1
  Faderfox_PC12_Pages/
    __init__.py
    pc12_surface.py         # ControlSurface; listens on ch 1, 2, 3
    pc12_cc_layout.py       # CC constants (shared across pages)
    page_performance.py     # ch 1 binding: pots → sends/filters, btn → arm
    page_compression.py     # ch 2 binding: pots → comp, btn → comp enable
    page_eq.py              # ch 3 binding: pots → EQ Eight bands, btn → bypass
    track_device_finder.py  # Locates Auto Filter / Compressor / EQ Eight
```

Two scripts (one per device). Each follows the same pattern: a single
`ControlSurface` subclass that creates `EncoderElement` / `ButtonElement` /
`SliderElement` instances per (channel, CC) and binds them to track parameters
through standard Live components or direct `_Parameter.value = …` writes.

The PC12 script holds the three page bindings as data tables (one per channel)
and feeds each one into the same element-creation loop, so the three pages
share one binding code path.

## Open decisions

Decisions resolved during planning:

- PC12 Compression row F = Compressor output (makeup) gain.
- PC12 Performance HP/LP = bands 1 and 2 of the **filter EQ Eight** (the
  second `Eq8` in each track's device chain). The first `Eq8` is the tonal
  EQ used by the EQ page.
- MX12 encoder turn = scene select, push = scene launch.

Still to resolve at first run in Live (tracked in `SHORTCUTS.md`):

- Verify Live API strings: Compressor `class_name`, Compressor parameter
  names, EQ Eight per-band parameter names. The script silently no-ops on
  wrong strings — verify by wiggling each control during the first test pass.
- Verify `MixerComponent(num_returns=4, ...)` kwarg is accepted by the
  current Live's v2 API.
- Decide whether the MX12 scene-select encoder should switch from absolute
  to relative mode (current implementation is absolute, may feel jumpy with
  many scenes).
- Decide whether direct-write linear scaling (`parameter.value = min + midi/127
  * (max - min)`) needs a logarithmic alternative for EQ band frequencies.

## Implementation notes worth keeping in the contract

- The PC12 script auto-rebinds device parameters when tracks are added/
  removed and when any track's device chain changes (`listens_group("devices")`
  on `song.tracks`). User can add/move EQ Eight / Compressor on the fly
  without restarting Live.
- The compressor on/off and tonal-EQ on/off green buttons toggle
  `device.is_active` directly. This matches Live's device on/off LED in the
  GUI.
- MX12 row A pots (top row of pots, CCs 1–12 on channel 1) are not declared as
  MIDI elements at all. They remain available to Live for ad-hoc Cmd+M user
  mapping. Row B (second-from-top) controls track pan.

## Non-goals

- No MIDI feedback to device LEDs/displays (PC12/MX12 don't expose displays
  to host the way EC4 does; LEDs only respond to button-state feedback by
  default, which Live handles automatically for solo/mute/arm).
- No support for cascading two devices via the EXTENSION port in this version.
  If the user later adds a second MX12 or PC12, we extend the mapping tables.
- No MIDI Remote Script support for setting up the *Live device chain* on each
  track. The user is responsible for adding Auto Filter / Compressor / EQ Eight
  to each track. The script only binds to them once present.
