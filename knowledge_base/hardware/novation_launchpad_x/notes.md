# Novation Launchpad X — programmer-mode notes

**Source:** `LaunchpadX_ProgrammersReference.pdf` (official, Focusrite/Novation), 29 pp,
read directly. Layout diagram on p.10; lighting on p.12–15; modes on p.7–9.
`LaunchpadX_UserGuide.pdf` also archived. Fetched 2026-06-03.

These are the verified facts for driving the LPX from a custom script.

## Modes — use Programmer mode for a custom script

- **Programmer mode** = full control: every pad/button sends a message and lights from
  the same message echoed back. Enter/exit via SysEx:
  - Enter Programmer: `F0 00 20 29 02 0C 0E 01 F7`
  - Back to Live mode: `F0 00 20 29 02 0C 0E 00 F7`
  - (Header for all LPX SysEx is `F0 00 20 29 02 0C`.)
  - Must enter on connect and **revert to Live mode on disconnect**, or the device is
    left stuck in Programmer mode.
- Two USB MIDI interfaces: **"LPX DAW In/Out"** (for the gated DAW/Session protocol) and
  **"LPX MIDI In/Out"** (Note/Custom/Programmer). Use the MIDI interface for Programmer mode.
- There is also a full **DAW mode** with a built-in Drum Rack layout, Session, and faders
  (p.16–22). More "batteries included" but a more complex protocol designed around Live's
  Session — for a bespoke step sequencer, Programmer mode is cleaner and was chosen.

## Button → message map (Programmer mode, p.10) — VERIFIED

All on MIDI channel 1.

- **8×8 grid pads → Note On**, note number = `row*10 + col`, bottom-left = `11`,
  top-right = `88`. (Bottom row 11–18, next 21–28, … top row 81–88.) Note Off = Note On
  velocity 0.
- **Top round row (8) → CC `91`–`98`** (left→right).
- **Right round column (8) → CC `19, 29, 39, 49, 59, 69, 79, 89`** (bottom→top).
- **Logo → CC `99`**.

> ⚠️ The grid's `11–88` is what the *Launchpad emits*. A Live **Drum Rack receives** on
> notes `36–51`. A script must **translate** LPX `11–88` ⇄ drum notes — they are not the
> same numbers. (Earlier confusion corrected here.)

## LEDs (p.12–15)

- Echo the pad's own note/CC back to light it. **Channel selects animation:**
  - ch1 (`90`/`B0`) = static · ch2 (`91`/`B1`) = flashing · ch3 (`92`/`B2`) = pulsing.
  - velocity / CC value = colour index from the 0–127 palette (p.12).
- **Batch RGB SysEx** (command `03`): light up to **81 LEDs in one message**, each as
  `<type> <index> <data...>` where type `0`=palette static, `1`=flashing, `2`=pulsing,
  `3`=RGB (r,g,b each 0–127). LED indices are the same `11–88` / CC numbers.
  → Use this for fast full-surface refreshes instead of one message per pad.

## Other

- Pads are **velocity- and aftertouch-sensitive** (both configurable: velocity curve,
  aftertouch mode, p.25–26). Played-in drum hits can be dynamic.
- Brightness, LED feedback, and aftertouch are configurable via SysEx (p.25–27).

## Relevance to `drum_programmer`

Confirms the chosen contract: Programmer mode, grid `11–88` for the 32-step area +
sound/pattern selectors, round buttons on CC `91–98` / `19–89` for editing functions,
batch-RGB SysEx for the playhead/step-state feedback. See the drum_programmer ARCHITECTURE
docs (to be written) for the full mapping.
