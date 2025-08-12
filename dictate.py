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
    if "\n" in text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return text
    paragraphs = []
    for i in range(0, len(sentences), 2):
        paragraphs.append(" ".join(sentences[i:i+2]))
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

    # 2) Simulate Cmd+V with AppleScript (works in most apps)
    as_cmd = [
        "osascript",
        "-e",
        'tell application "System Events" to keystroke "v" using command down'
    ]
    try:
        subprocess.run(as_cmd, check=True)
    except Exception as e:
        print(f"Paste key send failed: {e}")


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

        def on_press(key):
            nonlocal pressed_time
            if key == HOLD_KEY and not recording_flag.is_set():
                # Start recording
                while not audio_q.empty():
                    try:
                        audio_q.get_nowait()
                    except queue.Empty:
                        break
                recording_flag.set()
                pressed_time = time.time()
                play_sound(SOUND_START)
                # print("Recording...")

        def on_release(key):
            nonlocal pressed_time
            if key == HOLD_KEY and recording_flag.is_set():
                recording_flag.clear()
                duration = time.time() - pressed_time
                if duration < MIN_SPEECH_SECS:
                    # Ignore very short presses to avoid noise
                    return
                # Pull all buffered frames
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
                # Convert to mono 16k float32 and flatten to 1-D
                if audio.ndim == 2:
                    if audio.shape[1] > 1:
                        audio = np.mean(audio, axis=1)
                    else:
                        audio = audio[:, 0]
                audio = audio.astype(np.float32).reshape(-1)

                # Skip if the captured audio is still too short
                audio_seconds = float(len(audio)) / float(SAMPLE_RATE)
                if audio_seconds < 0.8:
                    print(f"Captured {audio_seconds:.2f}s (<0.8s). Skipping.")
                    return

                # Indicate stop recording
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

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
