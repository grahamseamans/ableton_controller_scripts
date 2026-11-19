# D16 Group Drumazon / Drumazon 2 — MIDI note → voice notes

**Sources (official, d16.pl, fetched 2026-09-24):**
- `Drumazon2-manual-gb.pdf` — Drumazon 2 user manual, 72 pp (PDF dated 2024-03-06).
- `Drumazon-manual-gb.pdf` — Drumazon (v1) user manual, 53 pp (PDF dated 2012-07-06).
  Not linked from d16.pl/manuals any more; still served at the same path.

`*.txt` beside each PDF = `pdftotext -layout`. Line numbers below refer to those; pages
are PDF page indices.

---

## Drumazon 2

External mode (Int Seq off) = sound module, one note per voice. Default map "follows the
General MIDI standard, as it does in the original 909" (`Drumazon2-manual-gb.txt` L1300, p.30).

The manual gives **no numeric table**. The mapping below is read off the Drum Map
screenshot on p.31 (keyboard labelled C0…C4 in the screenshot). Note numbers assume
the screenshot's C0 = MIDI 24, from the text on the same page: Drumazon "operates in a
4-octave MIDI range only (starting with the 3rd octave of the entire MIDI range)"
(L1344, p.31), i.e. 24–71. That assumption is **our inference**. It agrees with GM
(which the manual says the map follows) and with Live's naming, where 36 = C1.

| Note | Name (screenshot) | Voice |
|------|-------------------|-------|
| 35 | B0  | BD |
| 36 | C1  | BD |
| 37 | C#1 | RS (rim shot) |
| 38 | D1  | SD |
| 39 | D#1 | CP (clap) |
| 40 | E1  | SD |
| 41 | F1  | LT |
| 42 | F#1 | CH (closed hat) |
| 43 | G1  | LT |
| 44 | G#1 | CH |
| 45 | A1  | MT |
| 46 | A#1 | OH (open hat) |
| 47 | B1  | MT |
| 48 | C2  | HT |
| 49 | C#2 | CR (crash) |
| 50 | D2  | HT |
| 51 | D#2 | RD (ride) |

**User-configurable: yes.** Trigger view → Drum Map: select an instrument, then click keys
on the on-screen keyboard or use MIDI Learn. Restore the factory (GM) map, or load or save a
map file (L1310–1358, pp.30–31). Only notes inside the 4-octave window can be used (L1344).

**Velocity:** continuous, no separate accent step in External mode (L1303–1305, p.30).
Tap-record: velocity > 64 → accented step (L2011–2013, p.47).

**Host Note pattern mode** (a different mode): 48 notes from "the C note of the second
lowest octave" select patterns (L1498–1500, p.35).

**MIDI channel behaviour: not documented.** A grep for `channel|omni|midi ch` finds only
mixer "channel strip" text.

## Drumazon (v1)

- The drum map is GM-compatible and can be changed by the user (sidebar note, L46–57, p.4). In External mode,
  "The mapping follows the General Midi standard, the same as the original 909"
  (L134–136, p.6).
- **No note table or screenshot of the map in the text.** Per-note assignments are not
  documented beyond "General MIDI".
- Configurable: Drum map tab lets you load or save a `.drdrmap` file. You can set the default
  map to Factory (GM) or a User-defined file (L1351–1410, pp.45–46).
- **MIDI channel behaviour: not documented** (same grep, no hits).
