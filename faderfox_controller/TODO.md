# TODO — future ideas

## Replace per-track device discovery with a single macro rack per track

Today the PC12 script walks each track's device chain and looks for specific
classes (`Compressor2`, `Eq8` × 2). If the user reorders devices, adds wraps,
or uses a different compressor/EQ, the script silently no-ops.

**Better idea:** a single dedicated **Audio Effect Rack** per track that wraps
HP, LP, Comp, EQ in any internal order, with a fixed set of named macro
parameters that the PC12 script binds to. Layout would be something like:

- 8 macros: HP cutoff, LP cutoff, Comp threshold, Comp ratio, Comp attack,
  Comp release, Comp output gain, Comp on/off
- (or two racks: one for filtering + comp, one for EQ — depends on macro slots
  available; Live racks have 8 or 16 macros depending on version)

Then the script just binds to `track.devices[<rack_index>].parameters[N]`,
matching by macro name (`"HP Cutoff"`, `"LP Cutoff"`, etc.). Far more robust:

- Doesn't care what plugin lives inside the rack — could swap stock Compressor
  for FabFilter Pro-C2 without changing the script
- One device per track instead of three; cleaner mixer view
- User can save the rack as a preset and drop it on each new track in one click
- Survives device reordering and chain rewiring inside the rack
- Macro names = self-documenting

**Cost:** user has to set up the rack template once and put it on each of the
12 tracks. Probably worth it.

Defer until after current setup is fully working and we've used it for a
session or two — then we'll know if the convenience is worth the rebuild.
