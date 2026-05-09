# MIDI Mappings — Source of Truth

This file is the contract between the Faderfox devices and the Live scripts.
If the device sends `(channel, CC)` and this file claims a binding, the script
implements it. If a script does something this file does not document, the
script is wrong.

All CC numbers below come from the manufacturer's factory layout for generic
setups (1–20, 23–29 on MX12; 1–20, 25–29 on PC12). See `manuals/MX12_Manual_V04.pdf`
and `manuals/PC12_Manual_V04.pdf`, "Factory settings" sections.

---

## MX12 — Setup 1, Channel 1

| Control                | CC      | Live parameter                |
|------------------------|---------|-------------------------------|
| Fader 1–12             | 25–36   | Track 1–12 volume             |
| Pot row A (1–12)       | 1–12    | Track 1–12 pan                |
| Pot row B (1–12)       | 13–24   | (unbound — pots inert)        |
| Gray button 1–12 (row C) | 37–48 | Track 1–12 solo               |
| Green button 1–12 (row D) | 49–60 | Track 1–12 mute              |
| Encoder turn           | 61      | Scene select (proposed)       |
| Encoder push           | 62      | Scene launch (proposed)       |

---

## PC12 — Three pages, three setups

The PC12 sends the same CCs in every setup; only the channel differs.
Switching setups on the device = switching pages.

### PC12 — Setup 1, Channel 1 — Performance page

HP and LP cutoffs target the **filter EQ Eight** (the second `Eq8` in the
track's device chain). Bands 1 (HP) and 2 (LP) must be set to those filter
types manually on each track.

| Control            | CC      | Live parameter                                          |
|--------------------|---------|---------------------------------------------------------|
| Pot row A (1–12)   | 1–12    | Track 1–12 send 1                                       |
| Pot row B (1–12)   | 13–24   | Track 1–12 send 2                                       |
| Pot row C (1–12)   | 25–36   | Track 1–12 send 3                                       |
| Pot row D (1–12)   | 37–48   | Track 1–12 send 4                                       |
| Pot row E (1–12)   | 49–60   | Track 1–12 filter EQ Eight — band 1 (HP) frequency      |
| Pot row F (1–12)   | 61–72   | Track 1–12 filter EQ Eight — band 2 (LP) frequency      |
| Green button 1–12  | 73–84   | Track 1–12 record arm                                   |
| Encoder turn       | 85      | (unbound — TBD)                                         |
| Encoder push       | 86      | (unbound — TBD)                                         |

### PC12 — Setup 2, Channel 2 — Compression page

| Control            | CC      | Live parameter                                    |
|--------------------|---------|---------------------------------------------------|
| Pot row A (1–12)   | 1–12    | Track 1–12 Compressor — threshold                 |
| Pot row B (1–12)   | 13–24   | Track 1–12 Compressor — ratio                     |
| Pot row C (1–12)   | 25–36   | Track 1–12 Compressor — attack                    |
| Pot row D (1–12)   | 37–48   | Track 1–12 Compressor — release                   |
| Pot row E (1–12)   | 49–60   | Track 1–12 Compressor — knee                      |
| Pot row F (1–12)   | 61–72   | Track 1–12 Compressor — output gain (makeup)      |
| Green button 1–12  | 73–84   | Track 1–12 Compressor — device on/off             |

### PC12 — Setup 3, Channel 3 — EQ page

Targets the **tonal EQ Eight** (the first `Eq8` in the track's device chain).
Bands 1 (low shelf), 2 (bell), and 3 (high shelf) must be set to those filter
types manually on each track.

| Control            | CC      | Live parameter                                              |
|--------------------|---------|-------------------------------------------------------------|
| Pot row A (1–12)   | 1–12    | Track 1–12 tonal EQ Eight — band 1 (low shelf)  gain        |
| Pot row B (1–12)   | 13–24   | Track 1–12 tonal EQ Eight — band 1 (low shelf)  frequency   |
| Pot row C (1–12)   | 25–36   | Track 1–12 tonal EQ Eight — band 2 (bell)       gain        |
| Pot row D (1–12)   | 37–48   | Track 1–12 tonal EQ Eight — band 2 (bell)       frequency   |
| Pot row E (1–12)   | 49–60   | Track 1–12 tonal EQ Eight — band 3 (high shelf) gain        |
| Pot row F (1–12)   | 61–72   | Track 1–12 tonal EQ Eight — band 3 (high shelf) frequency   |
| Green button 1–12  | 73–84   | Track 1–12 tonal EQ Eight — device on/off                   |

---

## Channel collision check

The MX12 sits on channel 1 (setup 1).
The PC12's Performance page also sits on channel 1 (setup 1).

This is **not** a conflict because each device shows up as its own MIDI port to
Live ("Faderfox MX12" vs "Faderfox PC12") and the scripts are bound to specific
ports. Live routes incoming MIDI to the correct script based on port, not
channel. Confirmed by Faderfox's own factory documentation, which expects this.

If the user ever wants to keep them on truly distinct channels (e.g. for use
without Live), the MX12 can be moved to setup 5 (channel 5) or any other unused
slot — the script just reads a different constant.
