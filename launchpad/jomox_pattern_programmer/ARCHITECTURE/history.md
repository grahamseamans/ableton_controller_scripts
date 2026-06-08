# Architecture History

## Pattern 1 — Generic Launchpad drum sequencer over a Live Drum Rack
**Considered:** initial sketch (when the project was `drum_programmer`). Top half = 32-step
sequencer, bottom quarters = sound/pattern select, driving a software Drum Rack.

**Abandoned because:** the real target turned out to be the **Jomox AlphaBase hardware**
(project renamed `jomox_pattern_programmer`), whose interesting MIDI behaviour a plain
Drum Rack doesn't address. Superseded before any code.

## Pattern 2 — AlphaBase native mode: 11 channels, full chromatic pitch
**Considered:** AlphaBase native mode puts each instrument on its own channel (1–11) with
note number = full chromatic pitch (manual §13.1.1). This would give per-step chromatic
tuning of every drum — the richest version of the "hold step → assign note" idea.

**Abandoned because:** a single Live MIDI track outputs on **one channel only** — Live
re-channelizes all track output to the one "MIDI To" channel (Live 12 manual, Routing and
I/O). Verified that neither a remote script (bound to its own surface port, one port per
instance) nor a Max for Live device (also re-channelized) can cleanly fan one clip out to
11 channels. Deeper reason: a clip note has a single pitch field, so one clip can't encode
*both* "which of 11 instruments" *and* "free pitch" — full pitch + 11 instruments
inherently needs 11 separate note streams = **11 tracks**. That conflicts with the user's
"standard MIDI clips on a track that persist" goal and adds heavy setup.

**Status:** abandoned in favour of Pattern 3. Revisit only if 4 tunings prove too limiting
(would require the 11-track template).

## Pattern 3 — AlphaBase channel-16 keymap, single track (current)
**Chosen:** run the AlphaBase in **channel-16 keymap mode** — one channel, note selects
instrument, 4 tunings per instrument (deltas 0/6/12/18 semitones; manual §13.1.1). One MIDI
track → channel 16 carries the whole kit.

**Why this won:**
- Collapses the multi-channel routing problem to a single track / single channel.
- "Standard MIDI clips" that persist with the set — exactly the stated requirement.
- **Patterns = clip slots** on the one track (bottom-right pads); no scenes needed.
- The signature "hold step → assign note, colour by note" feature survives as a 4-tuning
  picker (4 colours) — quantised, but real.
- The script is a pure **editor/display**; normal Live playback feeds the AlphaBase.

**Trade-off accepted:** 4 tunings per instrument instead of full chromatic.

**Status:** active. See `architecture.md` and `midi_mappings.md`. No code yet.

## Decision provenance

All hardware/Live facts were taken from the local `knowledge_base/` (Live 12 manual,
Launchpad X Programmer's Reference, AlphaBase manual §13.1.1, decompiled scripts,
structure-void) rather than re-derived — see those sources for receipts.
