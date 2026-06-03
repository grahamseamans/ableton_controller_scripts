import re

BASE_TRACK = 0
NUMBER_TRACKS = 16
LAST_TRACK = BASE_TRACK + NUMBER_TRACKS

# MIDI values
STATUS_MASK = 0xF0
CHAN_MASK = 0x0F

CC_STATUS = 0xB0
NOTEON_STATUS = 0x90
NOTEOFF_STATUS = 0x80
PITCHBEND_STATUS = 0xE0

STATUS_ON = 0x7F
STATUS_OFF = 0x00

# base settings
FaderfoxUniversal_CH1 = 12
FaderfoxUniversal_CH2 = 13

# setup 27, group 1 + 2
NOTE_SELECT_TRACK_BASE = 56

# setup 28, group 5
CC_SEND_SELECTED_TRACK_BASE = 56
CC_SCENE_SELECT = 59
CC_TRACK_SELECT = 60
CC_CROSSFADER_ASSIGN = 61
CC_PAN_SELECTED_TRACK = 62  # in pan mode
CC_VOLUME_SELECTED_TRACK = 63

NOTE_TRACK_VIEW = 120
NOTE_CLIP_VIEW = 121
NOTE_STOP_CLIP_SELECTED = 122
NOTE_LAUNCH_CLIP_SELECTED = 123
NOTE_ARM_SELECTED = 124
NOTE_MONITOR_SELECTED = 125
NOTE_SOLO_SELECTED = 126
NOTE_MUTE_SELECTED = 127

# setup 28, group 6
CC_TRACK_VOLUME_BASE = 40
CC_TRACK_PAN_BASE = 32
CC_TRACK_SEND1_BASE = 0
CC_TRACK_SEND2_BASE = 8
CC_TRACK_SEND3_BASE = 16
CC_TRACK_SEND4_BASE = 24
NOTE_MUTE_TRACK_BASE = 104
NOTE_LAUNCH_TRACK_BASE = 64
NOTE_STOP_TRACK_BASE = 72
NOTE_ARM_TRACK_BASE = 80
NOTE_MONITOR_TRACK_BASE = 88
NOTE_SOLO_TRACK_BASE = 96

# setup 28, group 7
CC_MACRO_BASE_SELECTED_TRACK = 48
CC_MACRO_HIGH_BASE_SELECTED_TRACK = 73
NOTE_RACK_TRACK_VIEW = 112
NOTE_RACK_ON_OFF = 113
NOTE_PREVIOUS_RACK = 114
NOTE_NEXT_RACK = 115
NOTE_SHOW_RACK = 116
NOTE_LOCK_RACK = 117
NOTE_PREVIOUS_TRACK = 118
NOTE_NEXT_TRACK = 119

# setup 28, group 8
CC_TEMPO_COARSE = 56
CC_TEMPO_FINE = 57
CC_QUANTIZATION = 58
CC_GLOBAL_SCENE_SELECT = 59
CC_GLOBAL_TRACK_SELECT = 60
CC_CUE_VOLUME = 61
CC_MASTER_PAN = 62
CC_MASTER_VOLUME = 63
NOTE_NUDGE_DOWN = 120
NOTE_NUDGE_UP = 121
NOTE_STOP_SCENE = 122
NOTE_START_SCENE = 123
NOTE_GLOBAL_PLAY = 124
NOTE_GLOBAL_STOP = 125
NOTE_GLOBAL_RECORD = 126
NOTE_SWITCH_ARRANGEMENT_VIEW = 127

NOTE_PARAMETER_DISPLAY_BASE = 40

# additional sends
CC_HIGH_SEND_SELECTED_TRACK_BASE = 64
CC_CROSSFADE = 48

NOTE_PREVIOUS_BANK = 112
NOTE_NEXT_BANK = 113

# device ids
FADERFOX_DEVICE_EC4 = 11

FADERFOX_DEVICE_NAMES = {
    FADERFOX_DEVICE_EC4: u'EC4'
}

DISPLAY_ROW_SIZE = 20
DISPLAY_ROW_COUNT = 4
DISPLAY_TOTAL_LENGTH = DISPLAY_ROW_COUNT * DISPLAY_ROW_SIZE

HIDE_TOTAL_DISPLAY = (
    0xF0, 0, 0, 0, 
    0x4E, 0x2C, 0x1B, 
    0x4E, 0x22, 0x15,
    0xF7
)

CLEAR_AND_HIDE_TOTAL_DISPLAY = (
    0xF0, 0, 0, 0, 
    0x4E, 0x2C, 0x1B, 
    0x4E, 0x22, 0x13,
    0x4A, 0x20, 0x10,
    *[item for _ in range(DISPLAY_TOTAL_LENGTH) for item in [0x4D, 0x22, 0x10]],
    0x4E, 0x22, 0x15, 
    0xF7
)

CLEAR_MAIN_DISPLAY = (
    0xF0, 0, 0, 0,
    0x4E, 0x2C, 0x1B,
    0x4E, 0x22, 0x10,
    0x4A, 0x20, 0x10,
    *[item for _ in range(64) for item in [0x4D, 0x22, 0x1D]],
    0xF7
)

EMPTY_ROW_CONTENT = " " * DISPLAY_ROW_SIZE
EMPTY_DISPLAY_CONTENT = " " * DISPLAY_TOTAL_LENGTH

DEVICE_DISPLAY_SETUPS = [12, 13, 14, 15]
DEVICE_DISPLAY_GROUPS = [2, 3]

NUM_DISPLAY_LINE_SEGMENTS = 16

SYSEX_START_BYTE = 0xF0
SYSEX_START = (SYSEX_START_BYTE, 0, 0, 0)
FADERFOX_EC4_DEVICE_ID = (0x4E, 0x2C, 0x1B)
SET_TEXT_MSG_HEADER = (0x4E, 0x22, 0x10)
BASE_ADDRESS_MSG_HEADER = (0x4A, 0x20, 0x10)
SET_PROPERTY_MSG_HEADER = (
    SYSEX_START
    + FADERFOX_EC4_DEVICE_ID
    + SET_TEXT_MSG_HEADER
    + BASE_ADDRESS_MSG_HEADER
)
SYSEX_END_BYTE = 0xF7
SYSEX_END = (SYSEX_END_BYTE,)

SETUP_COUNT = 16
GROUP_COUNT = 16

EC4_SYSEX_BUTTON_IDENTIFIER = ( 0xF0, 0x00, 0x00, 0x00, 0x4E, 0x2C, 0x1B, 0x4e )

EC4_SYSEX_SHIFT_BUTTON = ( 0x26, 0x11, 0x4e, 0x2e )
EC4_SYSEX_USER_BUTTONS = [
    ( 0x26, 0x12, 0x4e, 0x2e ),
    ( 0x26, 0x13, 0x4e, 0x2e ),
    ( 0x26, 0x14, 0x4e, 0x2e ),
    ( 0x26, 0x15, 0x4e, 0x2e ),
]

def get_ec4_bp_sysex_button( button_index ):
    return ( 0x2a, 0x10 + button_index, 0x4e, 0x2e )

GLOBAL_DISPLAY_ROW_TEMPLATE_NAME_LENGTH = 15
GLOBAL_DISPLAY_ROW_TEMPLATE = "{label:3}: {name:15}"

class NavPosition:
    First = -2
    Prev = -1
    Next = 1
    Last = +2

CHARS = {char: idx for idx, char in enumerate("".join([
    '                ',
    '                ',
    ' !"# %&\'()*+,-./',
    '0123456789:;<=>?',
    ' ABCDEFGHIJKLMNO',
    'PQRSTUVWXYZÄÖ Ü§',
    ' abcdefghijklmno',
    'pqrstuvwxyzäö üà',
    '  ²³            ',
    '          ()    ',
    '@               ',
    '                ',
    '    _           ',
    '                ',
    '                ',
    '          [\\]<|>'
]))}
CHARS[' '] = 0x20

def translate_string(string):
    if not string:
        return ''
    translated = ''.join([chr(CHARS[char] if char in CHARS else 0x1F) for char in string])
    return re.sub(r'\s+', ' ', translated)
