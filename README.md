# Local Push-to-Talk Dictation (macOS)

A tiny, offline, push-to-talk dictation tool for macOS using faster-whisper. Hold Right Option to record; release to transcribe and auto-paste into the focused app.

## Features
- Hold-to-talk hotkey (Right Option by default)
- Local transcription via faster-whisper (no API keys, no costs)
- Auto-paste result into the frontmost app
- Works system-wide

## Requirements
- macOS 13+
- Python 3.10+
- Microphone access

## Install
```bash
git clone https://github.com/TheKhozaChain/Dictation_APP.git
cd Dictation_APP
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

Download a Whisper model on first run (the script auto-downloads). For best balance: `small`, or if you have Apple Silicon try `medium` for accuracy.

## Usage
- Grant permissions when prompted:
  - Microphone: first audio use
  - Accessibility (for keystroke paste): System Settings → Privacy & Security → Accessibility → enable Terminal (or iTerm/your shell)

Run:
```bash
python dictate.py
```
Hold Right Option to speak; release to paste.

### Options
- Press Enter after paste: set `WILLOW_PRESS_ENTER=1`
- Double‑tap toggle (hands‑free): set `WILLOW_DOUBLE_TAP=1` (default on)
  - Double‑tap Right Option to toggle; single‑hold still works
- Per‑app allow/deny: `WILLOW_ALLOW_APPS="Cursor,Notes,TextEdit"` or `WILLOW_DENY_APPS="1Password"`

## Customize
Environment variables:
```bash
export WILLOW_LOCAL_MODEL=small       # tiny, base, small, medium, large-v3
export WILLOW_LOCAL_LANG=en           # None for auto
export WILLOW_LOCAL_DEVICE=auto       # auto/cpu/cuda
export WILLOW_LOCAL_PRECISION=int8    # float16/float32/int8
# Priority 2
export WILLOW_INPUT_DEVICE=""        # device name or index; empty=default
export WILLOW_LOG_TRANSCRIPTS=1       # 0 to hide transcript text from logs
export WILLOW_LOG_MAX_MB=2            # rotate log when size >= 2MB; 0 disables
# Priority 3
export WILLOW_PASTE_APPEND_NEWLINE=0  # 1 to add newline after paste
export WILLOW_PASTE_APPEND_SPACE=0    # 1 to add space after paste
export WILLOW_TRIM_LEADING_SPACE=0    # 1 to trim leading spaces
```

Change hotkey: edit `HOLD_KEY` in `dictate.py` (e.g., `keyboard.Key.shift`, or a specific character key via `keyboard.KeyCode.from_char('`')).

## Troubleshooting
- If paste doesn’t work, ensure your terminal app is allowed under Accessibility.
- If audio is noisy, switch to Built-in Microphone (System Settings → Sound → Input).
- If latency is high, try a smaller model (e.g., `base` or `small`).

## Menu bar app (optional)
We include a lightweight menu bar controller that manages the background service:
```bash
pip install -r requirements.txt  # ensures rumps is installed
python menubar.py
```
It shows a mic icon (🎤 when running, ❌ when stopped) with options: Start, Stop, Restart, Open Log, Quit. No logins.

## .env file (optional)
Create a `.env` alongside `dictate.py` to persist settings across logins, for example:
```
WILLOW_PRESS_ENTER=1
WILLOW_DOUBLE_TAP=1
WILLOW_ALLOW_APPS=Cursor,Notes,TextEdit
WILLOW_LOCAL_MODEL=small
WILLOW_LOCAL_PRECISION=int8
WILLOW_INPUT_DEVICE=
WILLOW_LOG_TRANSCRIPTS=1
WILLOW_LOG_MAX_MB=2
WILLOW_PASTE_APPEND_NEWLINE=0
```

## Notes
- Everything runs locally; no network required after model download.
- This is a single-file utility for personal use; extend as needed (punctuation/commands, language switching, etc.).
