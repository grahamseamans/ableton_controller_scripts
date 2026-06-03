# Max for Live / Max — docs mirror notes

**Source:** mirror of `docs.cycling74.com` (official Cycling '74 Max docs), sections
`/apiref/`, `/userguide/`, `/vignettes/`, `/tutorials/`. ~261 pages. Fetched 2026-06-03
via `update.py` (source `max_for_live_docs`). Re-run that to refresh.

## What's here & the entry points that matter for us

- **Live Object Model (LOM)** — `apiref/lom/` — the object graph you script against from
  Max for Live (Song, Track, Clip, Device, DeviceParameter, DrumPad, etc.). This is the
  same model the Python remote scripts expose, documented more cleanly here. Start here.
- **Max JavaScript / V8 API** — `apiref/` — `js`/`v8` objects, used to write logic in M4L
  devices without patching everything.
- **User Guide / vignettes** — concepts, `live.*` objects (`live.object`, `live.observer`,
  `live.path`, `live.remote~`) that bridge a Max patch to the LOM.

## Why M4L is relevant (user flagged it as potentially "super useful")

M4L runs *inside* Live with full LOM access **and** real audio/MIDI in the patch — so
unlike the Extensions SDK it can do signal processing and MIDI. Where a remote script is
the right tool for driving hardware control surfaces, M4L is the right tool for building
custom devices/instruments/effects and in-Live automation that needs the LOM. The two can
be combined. (We'll decide per-feature which layer to use as the projects develop.)

> Note: the docs are a Next.js site; the mirror captures the server-rendered content
> (verified: the LOM page renders its full object list into the HTML).
