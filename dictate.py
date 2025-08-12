#!/usr/bin/env python3
import os
import sys
import queue
import time
import threading
from dataclasses import dataclass

import numpy as np
import sounddevice as sd
from pynput import keyboard
from faster_whisper import WhisperModel
import subprocess
import re

# -----------------------------
# Config
# -----------------------------
MODEL_SIZE = os.environ.get("WILLOW_LOCAL_MODEL", "small")  # tiny, base, small, medium, large-v3
LANGUAGE = os.environ.get("WILLOW_LOCAL_LANG", None)  # e.g., "en"; None -> auto
DEVICE = os.environ.get("WILLOW_LOCAL_DEVICE", "auto")  # auto/cpu/cuda
COMPUTE_TYPE = os.environ.get("WILLOW_LOCAL_PRECISION", "int8")  # float16/float32/int8
SAMPLE_RATE = 16000
CHANNELS = 1
HOLD_KEY = keyboard.Key.alt_r  # Right Option as push-to-talk
MIN_SPEECH_SECS = 1.0  # ignore ultra-short press
SOUND_ENABLED = os.environ.get("WILLOW_SOUND", "1") != "0"
SOUND_START = os.environ.get("WILLOW_SOUND_START", "/System/Library/Sounds/Pop.aiff")
SOUND_STOP = os.environ.get("WILLOW_SOUND_STOP", "/System/Library/Sounds/Ping.aiff")
PRESS_ENTER = os.environ.get("WILLOW_PRESS_ENTER", "0") == "1"
DOUBLE_TAP_ENABLED = os.environ.get("WILLOW_DOUBLE_TAP", "1") != "0"
DOUBLE_TAP_WINDOW = float(os.environ.get("WILLOW_DOUBLE_TAP_WINDOW", "0.35"))
ALLOW_APPS = os.environ.get("WILLOW_ALLOW_APPS", "").strip()
DENY_APPS = os.environ.get("WILLOW_DENY_APPS", "").strip()

# -----------------------------
# Audio capture
# -----------------------------

audio_q: "queue.Queue[np.ndarray]" = queue.Queue()
recording_flag = threading.Event()


def audio_callback(indata, frames, time_info, status):
    if status:
        # print(status, file=sys.stderr)
        pass
    if recording_flag.is_set():
        audio_q.put(indata.copy())


@dataclass
class Recorder:
    stream: sd.InputStream

    def __enter__(self):
        self.stream.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stream.stop()
        self.stream.close()


# -----------------------------
# Transcription
# -----------------------------

def load_model():
    print(f"Python: {sys.executable}")
    print(f"Loading model: {MODEL_SIZE} ({DEVICE}, {COMPUTE_TYPE})...")
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    return model


def transcribe_buffer(model: WhisperModel, pcm: np.ndarray) -> str:
    if pcm.size == 0:
        return ""

    # Disable VAD to avoid short-chunk errors; also ignore sub-0.8s audio
    seconds = float(len(pcm)) / float(SAMPLE_RATE)
    print(f"Audio seconds: {seconds:.2f} (VAD disabled)")
    if seconds < 0.8:
        return ""

    try:
        segments, info = model.transcribe(
            pcm,
            language=LANGUAGE,
            vad_filter=False,
            vad_parameters=None,
            beam_size=5,
            no_speech_threshold=0.5,
            condition_on_previous_text=False,
            temperature=0.0,
            word_timestamps=False,
        )
    except Exception:
        return ""

    text_parts = []
    for seg in segments:
        text_parts.append(seg.text)
    return " ".join(part.strip() for part in text_parts).strip()


# -----------------------------
# Formatting and paste helpers
# -----------------------------

def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;!?])", r"\1", text)
    return text

def _apply_spoken_commands(text: str) -> str:
    replacements = [
        (r"\bnew\s+line\b", "\n"),
        (r"\bnewline\b", "\n"),
        (r"\bnew\s+paragraph\b", "\n\n"),
        (r"\bnext\s+paragraph\b", "\n\n"),
        (r"\bperiod\b", "."),
        (r"\bfull\s*stop\b", "."),
        (r"\bcomma\b", ","),
        (r"\bquestion\s*mark\b", "?"),
        (r"\bexclamation\s*(point|mark)\b", "!"),
        (r"\bcolon\b", ":"),
        (r"\bsemicolon\b", ";"),
        (r"\bopen\s+quote\b", ' "'),
        (r"\bclose\s+quote\b", '" '),
    ]
    out = text
    for pat, rep in replacements:
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    return out

def _remove_fillers(text: str) -> str:
    # Remove common speech fillers (word boundaries, case-insensitive)
    patterns = [
        r"\buh+\b",
        r"\bum+\b",
        r"\bmm+\b",
        r"\bmmm+\b",
        r"\beh+\b",
        r"\bah+\b",
        r"\buh\-huh\b",
        r"\bum\-hmm\b",
    ]
    out = text
    for pat in patterns:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    # Collapse any leftover double spaces
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip()

def _auto_paragraph(text: str) -> str:
    # Respect explicit newlines first
    if "\n\n" in text:
        return text
    # Split sentences conservatively
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return text
    # Group into paragraphs of ~2-3 sentences depending on length
    paragraphs = []
    buf = []
    char_count = 0
    for s in sentences:
        buf.append(s)
        char_count += len(s)
        if len(buf) >= 3 or char_count > 240:
            paragraphs.append(" ".join(buf))
            buf = []
            char_count = 0
    if buf:
        paragraphs.append(" ".join(buf))
    return "\n\n".join(paragraphs)

def format_transcript(text: str) -> str:
    if not text:
        return ""
    text = _apply_spoken_commands(text)
    text = _remove_fillers(text)
    text = _normalize_whitespace(text)
    text = _auto_paragraph(text)
    return text

def play_sound(path: str):
    if not SOUND_ENABLED:
        return
    try:
        subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def paste_text_into_front_app(text: str):
    if not text:
        return
    # Use pbcopy for reliability across macOS versions
    try:
        p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        p.communicate(input=text.encode('utf-8'))
    except Exception as e:
        print(f"Clipboard copy failed: {e}")

    # 2) Simulate Cmd+V with AppleScript (works in most apps) unless denied/filtered
    if not _is_front_app_allowed():
        return
    as_cmd = [
        "osascript",
        "-e",
        'tell application "System Events" to keystroke "v" using command down'
    ]
    try:
        subprocess.run(as_cmd, check=True)
    except Exception as e:
        print(f"Paste key send failed: {e}")

    # 3) Optionally press Enter
    if PRESS_ENTER:
        try:
            subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 36'], check=True)
        except Exception as e:
            print(f"Enter key send failed: {e}")


def _get_frontmost_app_name() -> str:
    try:
        out = subprocess.check_output([
            "osascript", "-e",
            'tell application "System Events" to get name of first process whose frontmost is true'
        ])
        return out.decode("utf-8").strip()
    except Exception:
        return ""


def _parse_app_list(raw: str) -> set[str]:
    if not raw:
        return set()
    return {itm.strip() for itm in raw.split(",") if itm.strip()}


def _is_front_app_allowed() -> bool:
    name = _get_frontmost_app_name()
    allow = _parse_app_list(ALLOW_APPS)
    deny = _parse_app_list(DENY_APPS)
    if name == "":
        return True
    if allow:
        return name in allow
    if deny:
        return name not in deny
    return True


# -----------------------------
# Main loop
# -----------------------------

def main():
    # Prepare audio stream
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='float32',
        callback=audio_callback,
        blocksize=0,
        device=None  # default input device
    )

    model = load_model()

    with Recorder(stream):
        print("Hold Right Option to dictate. Release to auto-transcribe and paste. Ctrl+C to quit.")

        pressed_time = 0.0

        # Double-tap toggle tracking
        last_tap_time = 0.0
        latched_on = False

        def _start_recording():
            nonlocal pressed_time
            while not audio_q.empty():
                try:
                    audio_q.get_nowait()
                except queue.Empty:
                    break
            recording_flag.set()
            pressed_time = time.time()
            play_sound(SOUND_START)

        def _stop_and_transcribe():
            nonlocal pressed_time
            recording_flag.clear()
            duration = time.time() - pressed_time
            if duration < MIN_SPEECH_SECS:
                return
            chunks = []
            while not audio_q.empty():
                try:
                    chunk = audio_q.get_nowait()
                    chunks.append(chunk)
                except queue.Empty:
                    break
            if not chunks:
                return
            audio = np.concatenate(chunks, axis=0)
            if audio.ndim == 2:
                if audio.shape[1] > 1:
                    audio = np.mean(audio, axis=1)
                else:
                    audio = audio[:, 0]
            audio = audio.astype(np.float32).reshape(-1)
            audio_seconds = float(len(audio)) / float(SAMPLE_RATE)
            if audio_seconds < 0.8:
                print(f"Captured {audio_seconds:.2f}s (<0.8s). Skipping.")
                return
            play_sound(SOUND_STOP)
            print("Transcribing...")
            try:
                raw_text = transcribe_buffer(model, audio)
            except Exception as e:
                print(f"Transcribe failed: {e}")
                raw_text = ""
            text = format_transcript(raw_text)
            print(f"→ {text}")
            paste_text_into_front_app(text)

        def on_press(key):
            nonlocal pressed_time, last_tap_time, latched_on
            if key == HOLD_KEY:
                now = time.time()
                if DOUBLE_TAP_ENABLED and (now - last_tap_time) <= DOUBLE_TAP_WINDOW:
                    # toggle latch
                    last_tap_time = 0.0
                    latched_on = not latched_on
                    if latched_on and not recording_flag.is_set():
                        _start_recording()
                    elif not latched_on and recording_flag.is_set():
                        _stop_and_transcribe()
                    return
                last_tap_time = now
                # normal hold-to-talk start
                if not recording_flag.is_set():
                    _start_recording()

        def on_release(key):
            nonlocal latched_on
            if key == HOLD_KEY and recording_flag.is_set():
                if latched_on:
                    # In latched mode, release does nothing
                    return
                _stop_and_transcribe()

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
