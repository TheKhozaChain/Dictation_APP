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
cd /Users/siphokhoza/willow_competitor
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

## Customize
Environment variables:
```bash
export WILLOW_LOCAL_MODEL=small       # tiny, base, small, medium, large-v3
export WILLOW_LOCAL_LANG=en           # None for auto
export WILLOW_LOCAL_DEVICE=auto       # auto/cpu/cuda/metal
export WILLOW_LOCAL_PRECISION=int8    # float16/float32/int8
```

Change hotkey: edit `HOLD_KEY` in `dictate.py` (e.g., `keyboard.Key.shift`, or a specific character key via `keyboard.KeyCode.from_char('`')).

## Troubleshooting
- If paste doesn’t work, ensure your terminal app is allowed under Accessibility.
- If audio is noisy, switch to Built-in Microphone (System Settings → Sound → Input).
- If latency is high, try a smaller model (e.g., `base` or `small`).

## Notes
- Everything runs locally; no network required after model download.
- This is a single-file utility for personal use; extend as needed (punctuation/commands, language switching, etc.).
