# WhisperWriter — uputstvo na srpskom

Program koji sluša tvoj mikrofon i **kuca ono što izgovoriš** u bilo koji prozor (Word, browser, Notepad...). Radi potpuno lokalno na tvom računaru — besplatno, bez interneta i bez slanja snimaka bilo kome.

## Šta ti treba

- Windows 10 ili 11
- ~2,5 GB slobodnog prostora (program + model)
- Mikrofon (i onaj u laptopu je dovoljan)

## Instalacija (jednom, ~10 minuta)

**Korak 1.** Otvori PowerShell (Start meni → ukucaj "powershell") i nalepi jednu po jednu liniju:

```powershell
winget install --id Python.Python.3.11 -e
winget install --id astral-sh.uv -e
winget install --id Git.Git -e
```

Zatvori pa ponovo otvori PowerShell.

**Korak 2.** Preuzmi program i instaliraj biblioteke:

```powershell
git clone https://github.com/zoranradojevic/whisper-writer C:\whisper-writer
cd C:\whisper-writer
uv venv --python 3.11
uv pip install -r requirements.txt
```

**Korak 3.** Prvo pokretanje (skida model za prepoznavanje govora, ~500 MB, samo jednom):

```powershell
.venv\Scripts\python.exe run.py
```

Sačekaj poruku `Local model created.` — pojaviće se mali WhisperWriter prozor.

## Svakodnevno korišćenje

1. Dupli klik na **WhisperWriter-silent.vbs** u folderu programa — tihi start: bez ijednog prozora, samo ikonica pored sata (napravi sebi prečicu na desktop: desni klik na fajl → Send to → Desktop). Ako želiš da vidiš šta program radi (status, brzinu, greške), koristi **WhisperWriter.bat** — isti program, sa konzolom; kod tihog starta te poruke idu u `whisperwriter.log`.
2. Sačekaj da se pojavi prozor (30–60 sekundi — model se učitava; ikonica pored sata se vidi odmah), pa klikni **Start**.
3. Klikni mišem u polje gde želiš tekst.
4. **Drži F9**, izgovori rečenicu, **pusti F9** — tekst se sam otkuca.

Program radi u pozadini (ikonica dole desno pored sata). Gasi se desnim klikom na ikonicu → **Exit**.

## Korisna podešavanja

Sva podešavanja su u fajlu `src\config.yaml` (otvori ga u Notepad-u). Najčešće izmene:

```yaml
language: sr          # jezik diktiranja: sr, en, de, fr...
activation_key: f9    # ili mouse_middle (tockic misa), ctrl+alt+space...
recording_mode: hold_to_record   # ili press_to_toggle (klik = pocni, klik = zavrsi)
```

Posle izmene restartuj program.

**Savet:** `activation_key: mouse_middle` + `recording_mode: press_to_toggle` = klik na točkić miša pokreće snimanje, drugi klik ga završava — bez tastature.

## Ako tekst nije otkucan

Desni klik na ikonicu pored sata → **History (click = copy)** → tu su poslednje 3 izdiktirane rečenice. Klik na bilo koju je kopira celu, pa je nalepi sa **Ctrl+V**.

## Kada pogrešno čuje neku reč

Otvori `src\corrections.yaml` i dodaj liniju:

```yaml
pogrešno: ispravno
```

npr. `kemit: commit`. Važi odmah za sledeću rečenicu, ne treba restart. Program će ubuduće i sam ređe grešiti na toj reči.

## Problemi?

- **Ništa se ne dešava posle pokretanja** — sačekaj do minut: model se učitava pre nego što se prozor pojavi.
- **Prečica ne radi** — proveri da li si kliknuo **Start** u glavnom prozoru.
- **Loše prepoznaje** — pričaj razgovetnije i u tišoj prostoriji; dodaj problematične reči u `corrections.yaml`; ili u `config.yaml` stavi veći model (`model: medium` — tačniji ali sporiji).

Detaljnije uputstvo (na engleskom, sa izborom modela, GPU podešavanjima itd.): [README.md](README.md)

🇬🇧 This guide in English: [GUIDE.md](GUIDE.md)
