# Valhalla Supermassive — reference notes

Copied 2026-10-09 from the press repo (not fetched from the web: web access was denied in
the session that filed this, so valhalladsp.com was NOT consulted).

| file | source |
|---|---|
| `supermassive.json` | `/Users/cibo/audio-projects/studio/press/correspondence/001-attachments/supermassive.json` — headless JUCE 8 dump of the **VST3 v5.0.0** plugin, 2026-08-02, 1001-point write sweeps per parameter |
| `vst-introspection.md` | `/Users/cibo/audio-projects/studio/press/projects/valhalla-supermassive/vst-introspection.md` — the findings written up from that dump |

Still to fetch (official, not yet in this folder):
- https://valhalladsp.com/shop/reverb/valhalla-supermassive/
- https://valhalladsp.com/ (manual / mode descriptions, if a page exists)

## Measured facts (from `supermassive.json`)

19 parameters, in plugin order: `Mix`, `DelaySync`, `DelayNote`, `Delay_Ms`, `DelayWarp`,
`Clear`, `Feedback`, `Density`, `Width`, `LowCut`, `HighCut`, `ModRate`, `ModDepth`, `Mode`,
`Reserved1`–`Reserved4` (do nothing), `Bypass`.
All are declared **continuous** in VST3 (only `Bypass` is discrete), normalised 0..1.

- `getParamStringByValue` **ignores its value argument**: the plugin returns the current
  string for any value asked about. So a host's "string for value X" query is expected to lie.
- `Mode`: 22 names over 24 slots; top of travel wraps back to Gemini. Plateau centres
  (t = normalised value):
  Gemini 0.0415, Hydra 0.104, Centaurus 0.1455, Sagittarius 0.1875, Great Annihilator 0.229,
  Andromeda 0.2705, Lyra 0.3125, Capricorn 0.354, Triangulum 0.3955,
  Large Magellanic Cloud 0.4375, Cirrus Major 0.479, Cirrus Minor 0.5205, Cassiopeia 0.5625,
  Orion 0.604, Aquarius 0.6455, Pisces 0.6875, Scorpio 0.729, Libra 0.7705, Leo 0.8125,
  Virgo 0.854, Pleiades 0.8955, Sirius 0.9375, (Gemini again 0.9795).
  Default 0.041666 = Gemini.
- `Clear`: two plateaus, `"ClearedAgain "` (trailing space) 0..0.499 and `"Cleared"` 0.5..1.
  Acts on **change**, not value (vst-introspection.md). Centres 0.25 / 0.75. Default 1.0.
- `Delay_Ms`: piecewise, discontinuity at t = 0.8 (588.5 ms → 800 ms). Default 300 ms at 0.5.
- `LowCut`: linear 10 Hz–2 kHz. `HighCut`: linear 200 Hz–20 kHz.
- `Width`: bipolar ±100 %, zero at centre.
- `DelaySync`: Msec owns half the range; Triplet only at exactly 1.0. Default 0.25 = Msec.
