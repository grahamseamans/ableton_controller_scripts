# Jomox AlphaBase — MIDI implementation notes

**Source:** `AlphaBase_E.pdf` (official, jomox.de), OS 1.2, 122 pp. MIDI details in
§10 (p.82–84, settings) and §13.1 Appendix (p.111–116, the implementation chart).
Also fetched `AlphaBaseMk2_E.pdf` for cross-checking the Mk2.
Fetched 2026-06-03.

---

## The headline fact (answers "can we set pitch per instrument via MIDI channels?")

**Yes — and it's the AlphaBase's *native* mode, not a trick.** §13.1.1, p.111, verbatim:

> "Each instrument has its own channel to send or receive midi notes. The note
> number is added to the pitch of the instrument. The basic internal tuning is on
> note C1 (36) and is added from there on to the internal pitch."

So in native mode:
- **MIDI channel = which instrument** (fixed assignment, not user-remappable; p.82
  "all Midi channels are firmly assigned to the instruments or global channels").
- **Note number = pitch/tuning of that instrument**, where C1 (36) is the base
  tuning and other notes transpose up from there. Range 36–97 (C1–C6).

### Instrument → channel map (§13.1.1, p.111)

| Instrument            | Channel | Note range | CC param channel (§13.1.3) |
|-----------------------|---------|-----------|----------------------------|
| Kick Drum             | 1       | 36–97     | CH1                        |
| Snare (MBrane)        | 2       | 36–97     | CH2 ("MBRANE")             |
| Closed Hi-Hat         | 3       | 36–97     | CH3 (sample engine)        |
| Open Hi-Hat           | 4       | 36–97     | CH4                        |
| Clap                  | 5       | 36–97     | CH5                        |
| Rim Shot              | 6       | 36–97     | CH6                        |
| Crash                 | 7       | 36–97     | CH7                        |
| Ride                  | 8       | 36–97     | CH8                        |
| X1 Sample             | 9       | 36–97     | CH9                        |
| X2 Sample             | 10      | 36–97     | CH10                       |
| FM Synth (6-voice poly) | 11    | 36–97     | CH11                       |

(Samples share the same CC layout, "SAMPLE CH3–CH10", p.114.)

### The alternative: channel-16 "key map" mode (§13.1.1, p.111)

> "On channel 16, the Alpha Base offers a key mapping for all instruments. Each
> instrument maps 4 notes on the keyboard. The pitch is added according to the 4 notes."

One channel, **note number selects the instrument** (GM-drum-map style), 4 notes per
instrument with **fixed pitch deltas 0 / 6 / 12 / 18 semitones** — so only 4 tunings
per instrument, not chromatic.

| Instrument | Notes  | Pitch deltas (semitones) |
|------------|--------|--------------------------|
| Kick       | 36–39  | 0,6,12,18 |
| Snare      | 40–43  | 0,6,12,18 |
| Closed HH  | 44–47  | 0,6,12,18 |
| Open HH    | 48–51  | 0,6,12,18 |
| Clap       | 52–55  | … |
| Rim        | 56–59  | … |
| Crash      | 60–63  | … |
| Ride       | 64–67  | … |
| X1         | 68–71  | … |
| X2         | 72–75  | … |
| FM (fixed chord) | 76–79 | … |

So the two modes trade off **chromatic pitch (11 channels)** vs **single-channel
convenience (4 tunings only, channel 16)**.

---

## Other MIDI facts worth keeping

- **RxTrig** (p.84): receives note triggers on **channels 1–11**, plays assigned
  instruments. Can be turned off to avoid other gear's channels triggering it.
- **TxTrig** (p.83): sends notes of played instruments (sequencer or manual).
  Sequencer velocity is **63 normal / 127 accent**.
- **TxCC** (p.83): when turning an edit knob, sends that param's CC on the
  *instrument's* channel.
- **Program Change** (§13.1.2, p.112):
  - Instrument recall as Multi Kit: PC 0–127 on ch 1–11 (the instrument's channel)
  - Single Preset recall: ch 12 · Multi Kit recall: ch 13 · Sequence pattern recall: 0–63 on ch 14
- **Sound parameters** are CCs per instrument on its own channel (full tables
  p.112–115: Kick CH1, MBrane CH2, Samples CH3–10, FM CH11). Common ones: Volume=CC7,
  "Select Instrument for Multi Kit"=CC64.
- **Global FX** (reverb/delay) live on **channel 16** (§ p.116).
- Clock: `ClkSync` (sync to incoming MIDI clock), `TxClk` (send clock as master),
  works over DIN MIDI or USB (don't feed both). USB↔MIDI bridging via `USBMidi` (p.82–84).

---

## Implication for `drum_programmer` (the design wrinkle)

This is the crux of the user's "how does the MIDI device work then?" question.

A standard **Ableton Drum Rack outputs all pads on one MIDI channel** (note selects
the pad). That maps cleanly onto AlphaBase **channel-16 keymap mode** — but you'd be
stuck with only 4 tunings per instrument.

To use AlphaBase **native mode** (per-instrument channel, full chromatic pitch),
a single Drum Rack/track can't address 11 channels. The options:

1. **11 MIDI tracks**, each set to MIDI-out channels 1–11 → AlphaBase. The Launchpad
   "sound select" picks the track/instrument; the step grid writes notes whose
   *pitch* tunes that instrument.
2. **Remote script emits per-instrument-channel notes directly** (bypassing the
   one-channel clip model) — the script knows instrument→channel and sends on the
   right channel.
3. **Drum Rack with per-chain MIDI routing** (External Instrument per pad set to a
   different channel) — possible but fiddly.

→ This means the drum_programmer's "sound select = which instrument" maps to **MIDI
channel (1–11)**, and a step's pitch is a real musical choice, not just a trigger.
That's a different data model than the Live-Drum-Rack assumption we'd been using.
**Open question for the user:** is drum_programmer sequencing the AlphaBase hardware,
a software Drum Rack, or both? It changes the clip/track architecture. (Tracked for
the drum_programmer design discussion — not resolved here.)
