# HANDOFF — Ableton Remote Script for the press controller (Valhalla Supermassive)

Written 2026-10-09 for the Claude on the Ableton machine, which builds, installs and tests
the script. Nothing has been built yet: this folder only holds this file. ( •̀ᴗ•́ )و

Every claim below is tagged **[VERIFIED]** (checked on hardware or in a source cited next to it),
**[SOURCED]** (read in a cited file, not tested in Live) or **[GUESS]** (check it).

---

## 1. What to build

A Python MIDI Remote Script `press_supermassive/scripts/Press_Supermassive/` (plus
`ARCHITECTURE/architecture.md`, `ARCHITECTURE/midi_mappings.md`, `SHORTCUTS.md`, `TODO.md`),
in the same shape as `faderfox_controller/`. It drives the Supermassive on the **selected track**
from the press controller's 10 encoders and 3 buttons, and lights its 33 RGB LEDs.

User rules for the code (from `~/.claude/CLAUDE.md`):
- long descriptive variable names;
- **no silent failures**: anything that can fail logs loudly (`logger.error` + `show_message` for
  the important ones): parameter name not found, device not found, unexpected MIDI, firmware error
  SysEx, writes that raise;
- every guess marked `GUESS` in a comment, and logged in `SHORTCUTS.md` with a timestamp;
- don't commit unless asked.

## 2. Model it on (in this repo)

Framework: **`ableton.v2.control_surface`**, the same as the Faderfox scripts (Python 3, Live 12).
- `faderfox_controller/scripts/Faderfox_PC12_Pages/__init__.py`: `create_instance` pattern.
- `faderfox_controller/scripts/Faderfox_PC12_Pages/pc12_surface.py`: `ControlSurface` subclass,
  elements built in `component_guard()`, `element.add_value_listener` + direct
  `parameter.value = …` writes, `@listens` / `@listens_group(...).replace_subjects(...)` to follow
  chain changes, `process_midi_bytes` override for RX logging, `disconnect` cleanup.
- `faderfox_controller/scripts/Faderfox_PC12_Pages/track_device_finder.py`:
  `find_named_parameter_on_device` (find by name). Note that the Faderfox version **returns None
  silently**; the press version must log every name it can't find.
- `faderfox_controller/ARCHITECTURE/*.md`, `SHORTCUTS.md`, `TODO.md`: shape of the docs.

Live API references (all in `knowledge_base/ableton/scripting/`):
| fact | source |
|---|---|
| `update_display()` ticks every `TIMER_DELAY = 0.1` s, with an `update_display_hook()` to override. Use it to flush LEDs | `midi_remote_scripts/Live12/ableton/v2/control_surface/control_surface.py` (`update_display`), `defaults.py` |
| SysEx in: `process_midi_bytes` sees all sysex. Unknown sysex is only `logger.warning`ed. Override it and decode `F0 7D 70 7F …` yourself. `_install_forwarding` for sysex makes no Live call, so Live hands the script all sysex | same `control_surface.py`, `process_midi_bytes` / `_install_forwarding` |
| SysEx out: `self._send_midi(tuple_of_bytes)` | same file, `_send_midi` / `_do_send_midi` |
| Note-off (0x80) is forwarded to the same `ButtonElement` as note-on, with value = velocity (0) | `.../v2/control_surface/input_control_element.py` `identifier_bytes` (status − 16), `midi.py` `extract_value` |
| `EncoderElement(MIDI_CC_TYPE, ch, cc, Live.MidiMap.MapMode.relative_two_compliment)`: the value listener gets the **raw** byte. Decode it yourself. Live's `normalize_two_compliment` treats 64 as +64 | `.../v2/control_surface/elements/encoder.py` |
| `DeviceParameter.value_items` **raises if `is_quantized` is False**. `str_for_value(v)` exists. `display_value` + `add_display_value_listener` exist in Live 12 | `midi_api/structure_void_mirror/.../reference/live12/Live.DeviceParameter.runtime/index.html` |
| `str(parameter)` = the current display string (stock idiom) | `Live12/Move/display_util.py:24`, `Live12/Push2/model/repr.py:51` |
| Find plugins with `isinstance(d, Live.PluginDevice.PluginDevice) and d.name.startswith(...)` | `Live12/Komplete_Kontrol_S_Mk3/focus_follow.py:31`, `Live12/MiniLab_3/analog_lab.py:22` |
| Plug-ins with ≤ 64 parameters show all of them in Live's panel (Supermassive has 19) | Live 12 manual §23.3.1, p. 448 (`knowledge_base/ableton/live_manual/live12-manual-en.pdf`) |

## 3. Controller facts [VERIFIED on hardware 2026-10-09]

Source of truth: `/Users/cibo/audio-projects/studio/press/firmware/README.md` and
`press_controller/board_valhalla_supermassive.h` (`ENCODERS`, `BUTTONS`, `LAMPS_IN_CHAIN_ORDER`).

- USB MIDI port: **"press controller"** (also a CDC serial port with the same name, for debug only).
- All channel messages go out on **MIDI channel 1** (channel index 0).

### Encoders: relative CC, two's complement
One message per encoder carries the detents counted since the last message:
`1..63` = +1..+63 (clockwise), `127..65` = −1..−63. The firmware clamps at ±63, so **0 and 64
never arrive**. Log them as unexpected if they do. One detent is one step.

| CC | control | lamp (LED index) |
|---|---|---|
| 20 | feedback | 25 feedback_lamp |
| 21 | modrate | 28 modrate_lamp |
| 22 | highcut | 29 highcut_lamp |
| 23 | width | 32 width_lamp |
| 24 | delay_ms | 23 delay_ms_lamp |
| 25 | delaywarp | 24 delaywarp_lamp |
| 26 | density | 26 density_lamp |
| 27 | moddepth | 27 moddepth_lamp |
| 28 | lowcut | 30 lowcut_lamp |
| 29 | mix | 31 mix_lamp |

Encoder pushes are not wired.

### Buttons
Press = note-on velocity 127. Release = note-off (status 0x80) velocity 0. 5 ms debounce.
| note | control |
|---|---|
| 36 | mode_prev |
| 37 | mode_next |
| 38 | clear (lamp 22 clear_lamp) |

### LEDs: SysEx in
```
F0 7D 70 01 <start> <r> <g> <b> [<r> <g> <b> ...] F7
```
`7D` = non-commercial manufacturer ID, `70` = press device tag, `01` = set LEDs. `<start>` is the
0-based **chain** index. Colour values are 0–127 (the firmware maps 127 to 255). LEDs not in the
message keep their colour. The whole chain is `<start>=0` + 33 triples (104 bytes). The firmware
scales the whole frame down if it would draw more than 400 mA (all-white is shown at ×0.81).
The script needs no current limiting of its own.

### Error replies: SysEx out
`F0 7D 70 7F <code> <offending command or 00> F7`. Log every one as an error:
| code | meaning |
|---|---|
| 01 | message does not start `7D 70 <command>` |
| 02 | unknown command |
| 03 | wrong length (needs `<start>` + whole r g b triples) |
| 04 | `<start>` + count runs past the end of the chain |
| 05 | message longer than the longest valid one; ignored whole |
| 06 | a status byte or a new `F0` arrived before `F7` |

### LED chain order (index → lamp), `LAMPS_IN_CHAIN_ORDER`
| idx | lamp | idx | lamp | idx | lamp |
|---|---|---|---|---|---|
| 0 | option_lamp_gemini | 11 | option_lamp_cirrus_minor | 22 | clear_lamp |
| 1 | option_lamp_hydra | 12 | option_lamp_cirrus_major | 23 | delay_ms_lamp |
| 2 | option_lamp_centaurus | 13 | option_lamp_large_magellanic_cloud | 24 | delaywarp_lamp |
| 3 | option_lamp_sagittarius | 14 | option_lamp_triangulum | 25 | feedback_lamp |
| 4 | option_lamp_great_annihilator | 15 | option_lamp_pisces | 26 | density_lamp |
| 5 | option_lamp_andromeda | 16 | option_lamp_scorpio | 27 | moddepth_lamp |
| 6 | option_lamp_lyra | 17 | option_lamp_libra | 28 | modrate_lamp |
| 7 | option_lamp_capricorn | 18 | option_lamp_leo | 29 | highcut_lamp |
| 8 | option_lamp_aquarius | 19 | option_lamp_virgo | 30 | lowcut_lamp |
| 9 | option_lamp_orion | 20 | option_lamp_pleiades | 31 | mix_lamp |
| 10 | option_lamp_cassiopeia | 21 | option_lamp_sirius | 32 | width_lamp (tail) |

**The chain order is NOT the plugin's mode order** (for example, plugin slot 8 is Triangulum but
LED 8 is Aquarius). Map by name: lower-case the plugin's mode string, replace spaces with `_`, then
look up `option_lamp_<that>`. All 22 names match this rule. Checked against the list in §4.

## 4. Supermassive reference [SOURCED: measured dump, not the manual]

Filed at `knowledge_base/plugins/valhalla_supermassive/` (`notes.md`, `supermassive.json`,
`vst-introspection.md`). It is a headless dump of **VST3 v5.0.0**, made 2026-08-02 with write
sweeps. **valhalladsp.com was NOT fetched**: web access was denied in this session. To fetch:
https://valhalladsp.com/shop/reverb/valhalla-supermassive/ .

The plugin's own parameter names, which the script should look up **by name** (never by index):
`Feedback`, `ModRate`, `HighCut`, `Width`, `Delay_Ms`, `DelayWarp`, `Density`, `ModDepth`,
`LowCut`, `Mix`, `Mode`, `Clear`. Not on the panel: `DelaySync` (the press design pins it to
**Msec, 0.25**. Optional for v1; ask the user), `DelayNote`, `Reserved1–4` (no effect), `Bypass`.

Findings that change the design:
1. **Every parameter is declared continuous**, Mode and Clear included. So in Live
   `is_quantized` is probably False, and **`value_items` will raise**. Don't use it.
2. **The plugin ignores the value in "string for value"**: it returns the *current* string
   whatever value you ask about. So `str_for_value(v)` should not be trusted to name a mode.
   Use **`str(parameter)`**, the current display string, to read the current mode name.
3. **Mode**: 22 names over 24 slots, and the top of travel wraps back to Gemini. Use the measured
   plateau centres to *write* a mode (plugin order):
   Gemini 0.0415, Hydra 0.104, Centaurus 0.1455, Sagittarius 0.1875, Great Annihilator 0.229,
   Andromeda 0.2705, Lyra 0.3125, Capricorn 0.354, Triangulum 0.3955, Large Magellanic Cloud 0.4375,
   Cirrus Major 0.479, Cirrus Minor 0.5205, Cassiopeia 0.5625, Orion 0.604, Aquarius 0.6455,
   Pisces 0.6875, Scorpio 0.729, Libra 0.7705, Leo 0.8125, Virgo 0.854, Pleiades 0.8955, Sirius 0.9375.
   (These values are normalised 0..1. Scale them by `parameter.min/max` in case Live's range differs.)
4. **Clear**: 2 plateaus, `"ClearedAgain "` (trailing space) below 0.5 and `"Cleared"` at 0.5 and
   above. It **acts on change**, so one press = flip between 0.25 and 0.75.
5. `LowCut` is linear 10 Hz–2 kHz and `HighCut` is linear 200 Hz–20 kHz, so the musical range sits
   in the bottom tenth. `Delay_Ms` jumps at 0.8 (588.5 → 800 ms). `Width` is bipolar with zero at
   the centre.

## 5. Behaviour the user decided

1. **Target device**: the Supermassive on `song.view.selected_track`, top-level chain. Follow
   `selected_track` changes and that track's `devices` changes. If none is found, log once per change
   (name the track and the device names it does have) and show the **not-connected state**. Your call;
   suggested: all lamps dark except the clear lamp dim red. Document what you choose.
2. **Knobs**: each detent moves the parameter by a fixed fraction of `max − min`. Suggested is
   1/100 per detent, held in one per-parameter table so it can be tuned. Clamp to the range.
   Quantized parameters move one value per detent. Look parameters up by name and log loudly any
   name that's missing.
3. **Mode buttons** step Mode prev/next in plugin order. Read the current name with `str(param)`,
   find its index, ±1, and write that plateau centre. **Wrap** (Sirius → Gemini), as the plugin itself
   wraps; the user may say clamp. Light **only** the current mode's lamp, chosen by mode **name**.
   An unknown name logs loudly and lights no mode lamp.
4. **Clear button**: flip `Clear` (see §4.4). The clear lamp lights while the button is held.
5. **Knob lamps show the value**: brightness = normalised value (keep a small floor so 0 isn't
   "off"). Update them from parameter **value listeners** (`@listens_group("value")`), so mouse and
   automation changes show too. Listeners only mark the frame dirty. `update_display_hook` sends at
   most one 33-LED SysEx frame per 100 ms tick, and only when something changed. Send a full frame on
   connect, on `refresh_state`/`port_settings_changed`, and a dark frame on `disconnect`.
6. **Cleanup**: drop every parameter, device and track listener when the device or track changes and
   on `disconnect`.

Keep the pure logic in functions with no `Live` imports so it can be unit-tested with stubs:
relative decoding, value → colour, mode name → lamp index, SysEx frame building, error-reply
decoding. `python3 -m py_compile` every file.

## 6. GUESSES: verify in Ableton (each one → `TODO.md` + `SHORTCUTS.md`, 2026-10-09)

1. **Device name**: Live names the device `ValhallaSupermassive` (the plugin name in the dump), so
   matching `"supermassive"` in `device.name`, case-insensitive, finds it. A renamed device or a
   Supermassive inside a rack is missed. Print `[(d.class_name, d.name) for d in track.devices]`.
   Expect `class_name == "PluginDevice"`. An AU instance is `"AuPluginDevice"` (`Live12/LV2_LX2_LC2_LD2/FaderfoxHelper.py:183`).
2. **Parameter names in Live** are the plugin's names exactly (`Delay_Ms` with the underscore,
   `ModRate`, …), plus Live's own `"Device On"` at index 0. Print `[p.name for p in device.parameters]`.
3. **Range**: the plugin parameters show `min == 0.0, max == 1.0` in Live. Print them.
4. **`is_quantized` is False for Mode and Clear**, so `value_items` raises. Check.
5. **`str(mode_param)` returns the mode name** (e.g. `"Gemini"`) and updates right after a write.
   If the string lags, the lamp lags one step. Also check whether `str_for_value` really does ignore
   its argument through Live.
6. **The Mode plateau centres from the VST3 dump also hold in Live**, and for the AU build if that
   is what gets loaded.
7. **One Clear flip clears the tails**, and two quick presses clear twice.
8. **Step size**: 1/100 per detent feels right. It is probably too coarse for LowCut/HighCut (≈20 Hz
   and ≈200 Hz per detent) and too slow for fast spins. Consider acceleration or a finer cutoff step.
9. **Lamp colours, brightness floor and not-connected look**: all to taste.
10. **Install path (Live 12, macOS)**: `~/Music/Ableton/User Library/Remote Scripts/Press_Supermassive/`,
    then choose the script in Settings → Link, Tempo & MIDI, with Input and Output = "press controller".
    **Not sourced**: the Live 12 manual has no remote-script install section, and the Ableton help
    article could not be fetched. The User Library default location *is* sourced (manual §4.7.6:
    `Macintosh HD/Users/<username>/Music/Ableton/User Library`). Fallback: the app bundle's
    `Contents/App-Resources/MIDI Remote Scripts/`.
11. **Logging**: `logging.getLogger(__name__)` output lands in Live's `Log.txt`. That is the
    Faderfox scripts' pattern and is unverified here. Find Log.txt under
    `~/Library/Preferences/Ableton/Live 12.x/`.
12. **Live delivers the firmware's error SysEx** to `receive_midi` / `process_midi_bytes`. Test it
    by sending a malformed frame on purpose (`F0 7D 70 01 00 7F F7` → expect `F0 7D 70 7F 03 01 F7`).

## Firmware

`firmware/press_controller.uf2` is the build running on the controller as of 2026-10-09 17:12
(includes the detent re-sync fix: every knob counts exactly one step per click, verified on
hardware). Source: `studio/press/firmware/press_controller/`; build and flash steps are in
`studio/press/firmware/README.md`. This file is a copy of a build output; rebuild from that
source rather than editing anything here. To flash: hold B, plug in USB, drag the .uf2 onto
the RPI-RP2 drive.
