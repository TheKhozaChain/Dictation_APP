## TO‑DO LIST — Local Dictation Tool (Willow‑style)

No changes have been made. This is a prioritized roadmap. Pick items and I’ll implement them next session.

### Priority 1 — High impact, low risk
- **Press Enter after paste (toggle)**
  - Add env var `WILLOW_PRESS_ENTER=1` (default off). After paste, send Enter for chat boxes (Claude in Cursor, Slack, etc.).
  - Acceptance: When enabled, pasted text submits messages in common chat UIs; disabled = no Enter.

- **Double‑tap to toggle (latched mode)**
  - Two quick taps of Right Option toggles “hands‑free” recording; single press still works as push‑to‑talk.
  - Acceptance: Double‑tap toggles ON/OFF, with start/stop chimes; hold still functions as today.

- **Per‑app allow/deny lists**
  - Env vars: `WILLOW_ALLOW_APPS="Cursor,Notes,TextEdit"` or `WILLOW_DENY_APPS="1Password"`.
  - Acceptance: Paste occurs only in allowed apps (or in all except denied ones).

- **Paragraphing improvements**
  - Group sentences into paragraphs by length/terminators; respect explicit spoken commands.
  - Acceptance: Long monologues auto‑split into readable blocks; “new paragraph” always forces a blank line.

- **Custom chimes (and quick toggle)**
  - Env vars: `WILLOW_SOUND=0|1`, `WILLOW_SOUND_START=/path/to.aiff`, `WILLOW_SOUND_STOP=/path/to.aiff`.
  - Acceptance: Sounds switchable or customizable without code edits.

### Priority 2 — Accuracy, performance, language
- **Model/precision presets**
  - Provide presets: `small` (fast), `base` (balanced), `medium` (more accurate). Recommend `medium + float16` on Apple Silicon.
  - Add optional pre‑download step to avoid first‑use delay.
  - Acceptance: One‑liner env changes apply at login via LaunchAgent.

- **Language control / auto‑detect toggle**
  - Env: `WILLOW_LOCAL_LANG=en` or empty for auto.
  - Acceptance: Locked language improves consistency/speed; auto works for mixed use.

- **Microphone selection**
  - Env: `WILLOW_INPUT_DEVICE="MacBook Pro Microphone"` or exact device name/index.
  - Acceptance: Tool uses the selected device regardless of system default.

- **Privacy & logs**
  - Env: `WILLOW_LOG_TRANSCRIPTS=0` to suppress transcript text in logs.
  - Add simple log rotation (size‑based). 
  - Acceptance: Logs exclude content when disabled; log file stays bounded.

### Priority 3 — UX polish, reliability, ops
- **Paste options**
  - Toggles: append trailing space/newline; optional trim leading space.
  - Acceptance: Text integrates cleanly with most editors/inputs.

- **Agent lifecycle helpers**
  - CLI shortcuts: `dictatectl restart|status|logs` wrappers for `launchctl` and tail.
  - Acceptance: One command to restart/check logs.

- **Config file**
  - Support `.env` or `config.toml` so settings persist without editing LaunchAgent.
  - Acceptance: Editing one file updates behavior on next restart.

- **On‑screen indicator (later)**
  - Optional menu bar indicator (recording/idle). Likely Swift/NSStatusBar or a lightweight Python menubar lib.
  - Acceptance: Visual state without opening logs.

### Priority 4 — Packaging & testing
- **Packaging**
  - Create a signed .app wrapper or menu bar app that embeds Python + model config; keep LaunchAgent option.
  - Acceptance: Double‑click app installs/starts; security prompts handled cleanly.

- **Basic tests**
  - Add tiny harness for: formatting (paragraphs, punctuation), filler removal, app allow/deny, paste flow (mocked).
  - Acceptance: CI‑style sanity checks before changes.

### Notes (current behavior verified)
- System‑wide paste into focused text field (Claude in Cursor, Notes, TextEdit, browsers, etc.).
- Start/stop chimes on press/release.
- Spoken commands: “new line”, “new paragraph”, “period”, “comma”, “question mark”, “exclamation point”.
- Filler removal: “um/uh/mm/mmm/eh/ah” variants.
- LaunchAgent auto‑starts on login; KeepAlive enabled.

### Implementation order (suggested)
1) Press‑Enter toggle
2) Double‑tap toggle mode
3) Per‑app allow/deny
4) Paragraphing improvements
5) Custom chimes toggle
6) Model/precision presets + pre‑download
7) Language control
8) Mic selection
9) Privacy/log rotation
10) Paste options
11) CLI helpers
12) Config file
13) Menu bar indicator
14) Packaging
15) Tests


