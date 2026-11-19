# Valhalla Supermassive — what the plugin turned out to be

Everything here was measured off the running plugin. Nothing came from a manual, because a
plugin has none. This is the research that produced the control mapping; the mapping itself
is `control_set.yaml`.

## Where the numbers came from

`../../correspondence/001-*` asked the Mac outside the devcontainer for a parameter dump.
`../../correspondence/001-attachments/supermassive.json` is the answer: VST3, v5.0.0, dumped
headlessly through JUCE 8.

The one thing that makes it trustworthy — Supermassive's `getParamStringByValue` **ignores its
value argument**, so a read-only sweep returns the same string 21 times. The dumping tool
detected that and fell back to *write* sweeps: set the parameter, read the string, restore it,
1001 points per parameter, with every parameter restored before each sweep so `DelayNote`'s
dependence on `DelaySync` could not contaminate anything.

The AU dump alongside it adds nothing — AU normalises 0..1 the same way and its display strings
are unformatted floats. That is a measured fact, not an assumption. **Don't dump AU again.**

## What the sweep found

| | |
|---|---|
| 19 parameters declared | only **13** are real; `Reserved1`–`4` display bare numbers and do nothing |
| `DelaySync` | 4 values, wildly uneven. `Msec` owns half the range; **`Triplet` exists only at exactly t = 1.0** |
| `Mode` | 22 names over 24 slots, and the top of travel **wraps back to `Gemini`** |
| `Delay_Ms` | piecewise, with a **discontinuity at t = 0.8** — jumps 588.5 → 800 ms |
| `LowCut` | linear 10 Hz–2 kHz, so 20–200 Hz sits in the first tenth of the knob |
| `HighCut` | linear 200 Hz–20 kHz, worse — below 2 kHz is the first 9% |
| `Width` | bipolar, ±100%, zero at centre |
| `Clear` | 2-state toggle that acts on *change*, not on value |

The rule that falls out: **enum and stepped parameters get a lookup table of measured plateau
centres, never a computed division of 0..1.** Anything that divides `DelaySync` into four equal
steps never reaches `Triplet` and hits `Msec` twice.

## What this plugin's mapping does with that

- **The panel is an opinionated subset, not a mirror.** 13 real parameters does not mean 13
  controls.
- **Dropped is not ignored.** Three states: *exposed* (gets a control), *pinned* (no control,
  the host script asserts it and owns it), *free* (left alone). `DelaySync` is **pinned to Msec
  at t = 0.25** — mid-plateau and the factory default. That also kills the
  `Triplet`-at-exactly-1.0 landmine outright, since we never go there.
- **`Mode` is a categorical with two buttons and a lamp per option**, and its 22 lamps get their
  real names on the panel. Long ones are shortened for silkscreen only — the export always
  carries the plugin's own string. The names themselves are never typed anywhere: they are
  derived from the sweep's measured plateaus. The two shortenings ARE a decision and are written
  down as one, in `control_set.yaml`.
- **`Width` is the only control here with a step point**, at its centre. press supports a list of
  points per knob; Supermassive needs exactly one, so it does not exercise that.
