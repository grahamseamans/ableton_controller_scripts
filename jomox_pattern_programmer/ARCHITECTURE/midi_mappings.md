# MIDI Mappings — Source of Truth

The contract between the Launchpad X, the script, and the Jomox AlphaBase. If the script
does something this file doesn't document, the script is wrong. All facts trace to the
knowledge base:
- Launchpad: `knowledge_base/hardware/novation_launchpad_x/` (Programmer's Reference, p.10–15)
- AlphaBase: `knowledge_base/hardware/jomox_alphabase/` (manual §13.1.1)

---

## A. Launchpad X — what the device sends/receives (Programmer mode)

Enter on connect: `F0 00 20 29 02 0C 0E 01 F7` · revert on disconnect: `F0 00 20 29 02 0C 0E 00 F7`.

| Control | Sends | Numbers |
|---|---|---|
| 8×8 grid pad | Note On, ch 1 (Note Off = vel 0) | `note = row*10 + col`, bottom-left `11` … top-right `88` |
| Top round row (×8) | CC, ch 1 | `91`–`98` (left→right) |
| Right round column (×8) | CC, ch 1 | `19,29,39,49,59,69,79,89` (bottom→top) |
| Logo | CC, ch 1 | `99` |

**LEDs:** echo the pad's note/CC. Channel = animation: ch1 static, ch2 flashing, ch3
pulsing; velocity/value = palette colour. **Batch RGB:** SysEx cmd `03`, up to 81 entries
`<type> <index> <r> <g> <b>` (type 3 = RGB, 0–127 each). Used for full-surface repaint.

---

## B. Launchpad grid → function regions

Grid coordinates `row*10+col`, row 8 = top, row 1 = bottom.

| Region | Grid pads (notes) | Function |
|---|---|---|
| Step sequencer (rows 8→5) | 81–88, 71–78, 61–68, 51–58 | 32 steps; step 1 = `81` (top-left), order left→right then top→down |
| Instrument select (rows 4→1, cols 1–4) | 41–44, 31–34, 21–24, 11–14 | instrument idx 0–15 (0–10 used), reading top→down, left→right |
| Pattern select (rows 4→1, cols 5–8) | 45–48, 35–38, 25–28, 15–18 | clip slot 0–15 |

Step→clip-time: `time = step_index * step_resolution` (default 1/16). step_index 0..31.
Instrument pad→idx: top-left of the quad (`41`) = idx 0, …, bottom-right (`14`) = idx 15.

Round buttons (CC) — initial assignment, see architecture.md "Round buttons":
top row `91–98` = step-res, accent, ghost, preview, clear, undo, nudge, Shift;
right col `19–89` = mute, solo, copy, paste, duplicate, +spare.

---

## C. AlphaBase — channel-16 keymap (manual §13.1.1)

**All notes on MIDI channel 16.** Note selects instrument; each instrument has 4 notes =
4 tunings (pitch deltas 0 / 6 / 12 / 18 semitones).

| idx | Instrument | Notes (tuning 0,1,2,3) |
|---|---|---|
| 0 | Kick | 36, 37, 38, 39 |
| 1 | Snare | 40, 41, 42, 43 |
| 2 | Closed HH | 44, 45, 46, 47 |
| 3 | Open HH | 48, 49, 50, 51 |
| 4 | Clap | 52, 53, 54, 55 |
| 5 | Rim | 56, 57, 58, 59 |
| 6 | Crash | 60, 61, 62, 63 |
| 7 | Ride | 64, 65, 66, 67 |
| 8 | X1 sample | 68, 69, 70, 71 |
| 9 | X2 sample | 72, 73, 74, 75 |
| 10 | FM synth | 76, 77, 78, 79 |

**Canonical formula:** `note = 36 + instrument_idx*4 + tuning`, `tuning ∈ {0,1,2,3}`.
This lives in code in `alphabase_map.py` as the single source; nothing else hard-codes notes.

Requires AlphaBase **RxTrig = on** (manual §10.3.3). Velocity→dynamics/accent: **to verify**.

---

## D. The full edit path (one step)

1. User selects instrument `i` (bottom-left) and pattern slot `p` (bottom-right).
2. Script binds to `track.clip_slots[p].clip` (creates an empty clip if needed).
3. User taps step `s` (rows 5–8). Script computes `note = 36 + i*4 + tuning(s)` and
   `time = s * step_resolution`, then toggles that note in the clip
   (`add_new_notes` / `remove_notes_extended`).
4. Holding step `s` + tapping a tuning pad changes `tuning(s)` (rewrites the note's pitch).
5. Live plays the clip out the track → channel 16 → AlphaBase. The script repaints LEDs
   (step colour = tuning; playhead = `clip.playing_position` mapped to a step cell).

---

## Channel summary

- Launchpad X ↔ script: ch 1 (its own MIDI port; LEDs + button input).
- Track → AlphaBase: **ch 16 only** (single track). No other channels used — this is the
  whole point of choosing keymap mode over native 11-channel mode.
