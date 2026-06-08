# TODO — future ideas

## FM synth as a separate melodic MIDI track (native ch11)

The AlphaBase's FM synth is a real **4-operator, up to 6-voice polyphonic** engine
(manual §13.1.1; CC table p.115), and in native mode it lives on **channel 11** with the
full chromatic note range **36–97 (C1–C6)**.

In the ch16 keymap that this project uses, the FM synth is reduced to just **4 notes
(76–79)** like every other instrument — fine as a drum voice, but it wastes the synth.

**Idea:** add a *second* track to the Live template — a normal **melodic MIDI track set to
channel 11** — so the FM synth can be played/sequenced chromatically (piano roll, or a
keyboard/other controller), independent of the ch16 drum programming. Hybrid setup:

- Track A → ch16 keymap → the 11 drum voices (this pattern programmer).
- Track B → ch11 → FM synth, melodic, full range.

Both go to the same AlphaBase MIDI port, different channels — no conflict (one track per
channel is exactly the supported multitimbral pattern). The pattern programmer itself
doesn't need to change; this is just an extra track in the template.

**Status:** deferred (user: "we can do that later"). Revisit after the core drum
programmer works.
