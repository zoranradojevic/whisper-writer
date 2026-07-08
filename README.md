# <img src="./assets/ww-logo.png" alt="WhisperWriter icon" width="25" height="25"> WhisperWriter

Speech-to-text for Windows: press a shortcut, speak, and the text types itself into any window. Runs 100% locally — free, no internet, nothing leaves your computer.

🇷🇸 [Uputstvo na srpskom](UPUTSTVO.md)

## Install (~10 minutes, once)

**Step 1** — open PowerShell and install the tools (skip what you have):

```powershell
winget install --id Python.Python.3.11 -e
winget install --id astral-sh.uv -e
winget install --id Git.Git -e
```

Close and reopen PowerShell.

**Step 2** — download the program:

```powershell
git clone https://github.com/zoranradojevic/whisper-writer C:\whisper-writer
cd C:\whisper-writer
```

**Step 3** — install dependencies:

```powershell
uv venv --python 3.11
uv pip install -r requirements.txt
```

**Step 4** — first run (downloads the speech model, ~500 MB, once):

```powershell
.venv\Scripts\python.exe run.py
```

Wait for `Local model created.` — a small window appears. Done.

## Use

1. Start the app: double-click **WhisperWriter-silent.vbs** (no windows, just a tray icon) or **WhisperWriter.bat** (with a console). Make a Desktop shortcut: right-click → Send to → Desktop.
2. Wait ~30–60 s for the window (model loading), click **Start**.
3. Click into any text field.
4. **Hold F9, speak, release F9** — the text types itself out.
5. Quit: right-click the tray icon → **Exit**.

## Customize

Open **Settings** in the app (or edit `src\config.yaml`):

- **Language**: `language: en` (or `sr`, `de`, `fr`, ... any Whisper code).
- **Shortcut**: click **Record** next to the activation key and press the keys or a mouse button you want. Tip: mouse wheel click + `press_to_toggle` mode = click to start, click again to stop.
- **Bigger model** = more accurate, slower: `model: medium` (default `small`). NVIDIA GPU: `device: cuda`, `compute_type: float16`, then `large-v3` is fast too.
- **Misheard words**: add `wrong: correct` lines to `src\corrections.yaml` — applies to the next sentence, no restart.

## If something goes wrong

- **Text wasn't typed?** Right-click the tray icon → **History** → click a sentence to copy it, then Ctrl+V.
- **Nothing happens on start?** Wait up to a minute — the model loads first. Silent-start logs are in `whisperwriter.log`.
- **Shortcut does nothing?** You must click **Start** in the main window first.

---

Fork of [savbell/whisper-writer](https://github.com/savbell/whisper-writer) with Windows startup fixes, mouse-button shortcuts, click-to-record shortcut capture, multiple alternative shortcuts, start/stop beeps, muting other apps while recording, a corrections dictionary with Whisper hotwords, a tray history menu, and a silent launcher.
