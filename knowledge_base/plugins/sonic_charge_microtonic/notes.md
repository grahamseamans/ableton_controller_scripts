# Sonic Charge Microtonic — MIDI note → voice notes

**Source (official, soniccharge.com, fetched 2026-09-24):** `Microtonic_User_Guide.pdf`,
guide for v3.3.4 (2022-11-07), 44 pp. `Microtonic_User_Guide.txt` = `pdftotext -layout`.
Line numbers refer to that .txt; pages are PDF page indices.

---

## Default key map, standard MIDI mode (table, L1419–1441, p.33)

C3 = middle C = 60 (L1440). This is the same naming Live uses.

| Keys | Note # | Function |
|------|--------|----------|
| C1–G1 | 36–43 | Trigger drum channel 1–8 (36=ch1 … 43=ch8) |
| C2–G2 | 48–55 | Mute channel 1–8 while held (sustain pedal CC64 holds mutes) |
| C3–B3 | 60–71 | Select pattern A–L |
| C4 | 72 | Stop/deactivate pattern engine |

Voices are generic "drum channels" 1–8, not fixed instrument types. What each one sounds
like depends on the patch (L92–95).

**User-configurable: yes.** Main Menu → Edit Midi Controllers / Keys. The rectangular markers
are assignable keys: click to learn, or drag to change. One key can drive several functions,
so you can layer sounds (L1380–1403, p.32). Custom keys are saved in `.scmc` MIDI config
files, not in presets. Reset restores factory defaults (L1362–1370, p.31). The pattern
engine's MIDI out uses the same keys (L1286–1291, p.30).

## MIDI channel behaviour

- **Standard mode:** listens on one Receive Channel, or on all channels if set to "any".
  Transmits on the Transmit Channel (L1340–1346, p.31). **The guide does not state the
  factory default Receive Channel.**
- **Pitched MIDI mode:** drum channels 1–8 = MIDI channels 1–8, full keyboard each, and
  60 (C3) = original pitch. MIDI ch 10 still works as in standard mode (L1351–1360,
  p.31). The table's keys "only respond on MIDI channel 10" in this mode (L1440–1441, p.33).
- Options: Stop voices on Note Off; Select drum channel with MIDI notes (L1274–1284, p.30).
