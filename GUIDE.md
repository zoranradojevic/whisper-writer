# WhisperWriter — simple guide

A program that listens to your microphone and **types what you say** into any window (Word, browser, Notepad...). Runs entirely locally on your computer — free, no internet needed, no recordings sent anywhere.

## What you need

- Windows 10 or 11
- ~2.5 GB of free disk space (program + model)
- A microphone (the built-in laptop one is fine)

## Installation (once, ~10 minutes)

**Step 1.** Open PowerShell (Start menu → type "powershell") and paste these lines one by one:

```powershell
winget install --id Python.Python.3.11 -e
winget install --id astral-sh.uv -e
winget install --id Git.Git -e
```

Close and reopen PowerShell.

**Step 2.** Download the program and install its libraries:

```powershell
git clone https://github.com/zoranradojevic/whisper-writer C:\whisper-writer
cd C:\whisper-writer
uv venv --python 3.11
uv pip install -r requirements.txt
```

**Step 3.** First run (downloads the speech-recognition model, ~500 MB, once only):

```powershell
.venv\Scripts\python.exe run.py
```

Wait for the message `Local model created.` — a small WhisperWriter window will appear.

## Everyday use

1. Double-click **WhisperWriter-silent.vbs** in the program folder — silent start: no windows at all, just an icon next to the clock (make yourself a Desktop shortcut: right-click the file → Send to → Desktop). If you want to see what the program is doing (status, speed, errors), use **WhisperWriter.bat** instead — same program, with a console; in silent mode those messages go to `whisperwriter.log`.
2. Wait for the window to appear (30–60 seconds — the model is loading; the tray icon shows up immediately), then click **Start**.
3. Click into the field where you want the text.
4. **Hold F9**, say a sentence, **release F9** — the text types itself out.

The program keeps running in the background (icon in the bottom-right corner, next to the clock). Quit it by right-clicking the icon → **Exit**.

## Useful settings

All settings live in `src\config.yaml` (open it in Notepad), or use the Settings window in the app. Most common changes:

```yaml
language: en          # dictation language: en, sr, de, fr...
activation_key: f9    # or mouse_middle (wheel click), ctrl+alt+space...
recording_mode: hold_to_record   # or press_to_toggle (click = start, click = stop)
```

Restart the program after editing.

**Tip:** `activation_key: mouse_middle` + `recording_mode: press_to_toggle` = click the mouse wheel to start recording, click again to finish — no keyboard needed. You can also record shortcuts by clicking **Record** next to the activation key field in Settings.

## If the text didn't get typed

Right-click the tray icon next to the clock → **History (click = copy)** → your last 3 dictated sentences are there. Click one to copy the whole sentence, then paste it with **Ctrl+V**.

## When it mishears a word

Open `src\corrections.yaml` and add a line:

```yaml
wrong: correct
```

e.g. `comit: commit`. Takes effect on the very next sentence, no restart needed. The program will also start hearing that word correctly more often on its own.

## Problems?

- **Nothing happens after starting** — wait up to a minute: the model loads before the window appears.
- **The shortcut doesn't work** — check that you clicked **Start** in the main window.
- **Poor recognition** — speak more clearly in a quieter room; add problem words to `corrections.yaml`; or set a bigger model in `config.yaml` (`model: medium` — more accurate but slower).

More detail (model choice, GPU setup, etc.): [README.md](README.md)

🇷🇸 Ovo uputstvo na srpskom: [UPUTSTVO.md](UPUTSTVO.md)
