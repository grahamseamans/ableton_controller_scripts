# Architecture History

## Pattern 1 — Use Faderfox's "Universal_2" V2.5 Live script as-is
**Tried:** initial setup. Drop the V2.5 script into Live's MIDI Remote Scripts,
use MX12 setup 30 (designed for that script).

**Abandoned because:** the V2.5 script is heavily EC4-targeted under the hood
(`FADERFOX_DEVICE_EC4 = 11`, EC4 sysex device IDs, EC4 button identifiers
embedded throughout). It works for the MX12's basic mix surface (faders/sends/
solo/mute share the same CCs across the Faderfox line) but cannot handle the
PC12's three-page workflow at all, and has no path to adapt the MX12's pot
rows to pan + inert. Also doesn't match the user's specific layout
(`goal.md`).

**Status:** abandoned in favor of writing custom scripts.

## Pattern 2 — Reprogram MX12 setup 30 onboard
**Tried:** detailed walkthrough produced for the user: 24 individual pot edits
(12 row A pots get CC remap from send 1 base → pan base; 12 row B pots get
channel moved off 13/14 to make script ignore them).

**Abandoned because:** even before the user started, the same logic applied to
the PC12 would be roughly 3 × 72 = 216 edits across three setups — clearly
wrong direction. Also: editing on-device couples the layout to muscle memory
of CC numbers rather than a readable script. Onboard programming is for
matching an existing protocol you don't control, not for designing a new one.

**Status:** abandoned without execution.

## Pattern 3 — Custom Live script with software-side page switching
**Tried (on paper only):** one PC12 setup, page state held in the Python script,
encoder-push held + green button N as a chord to switch pages.

**Abandoned because:** this fights the device. The Faderfox shift/snap buttons
are local-only modifiers (suppress data, switch setup, snap toggle); they don't
emit MIDI to the host. There are no spare buttons (PC12 has exactly 12, all
needed for per-channel functions). Encoder-push as a modifier works but is
clunky and inventing a paging system the device doesn't natively expose.

**Status:** abandoned during discussion (the user noticed we were fighting the
hardware).

## Pattern 4 — Channel-routed CC binding (current)
**Tried:** factory generic setups on both devices, no onboard reprogramming.
The PC12 uses three setups (1, 2, 3) for three pages; switching setups on the
device = switching pages, because the factory channel-per-setup convention
puts each page on its own MIDI channel. The Live script binds
`(channel, CC) → live parameter` with no internal mode state.

**Why this won:** Faderfox already designed this pattern. Setup 30 + the
Universal script is literally an instance of it (one setup → one channel →
one Live binding layout). We're just generalizing it across multiple setups
for paging. Zero onboard edits, zero modifier hacks, simple Python.

**Status:** active. See `architecture.md` and `midi_mappings.md`.
