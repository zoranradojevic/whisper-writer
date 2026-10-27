# WhisperWriter — uputstvo na srpskom

Program koji sluša tvoj mikrofon i **kuca ono što izgovoriš** u bilo koji prozor (Word, browser, Notepad, čet...). Radi na dva načina:

- **Preko interneta (preporučeno):** tekst stiže za ~2 sekunde i najtačniji je za srpski. Besplatno uz besplatne naloge na ElevenLabs i Groq (vidi dole).
- **Lokalno, na tvom računaru:** bez interneta i bez naloga, ali sporije (10–20 s čekanja).

Program sam bira: ako ima ključeve i internet, radi preko interneta; ako ne, lokalno.

## Šta ti treba

- **Windows 10 ili 11** (na Mac-u ne radi)
- ~4 GB slobodnog prostora
- Mikrofon (i onaj u laptopu je dovoljan)

## Instalacija (jednom, ~10 minuta)

1. Na stranici https://github.com/zoranradojevic/whisper-writer klikni zeleno dugme **Code** → **Download ZIP**.
2. Desni klik na skinuti ZIP → **Extract All** (Raspakuj sve) → izaberi npr. `C:\whisper-writer`.
3. U raspakovanom folderu dupli klik na **INSTALIRAJ.bat**.
   - Ako Windows kaže *"Windows protected your PC"*: klikni **More info** → **Run anyway**.
4. Prvo pita **jezik diktiranja**: srpski (Enter), engleski, nemački, **auto** (za one koji mešaju jezike) ili bilo koji drugi jezik (npr. `fr`, `hr`). Za druge jezike nastavlja na engleskom, a ekavica i brisanje poštapalica rade samo za srpski.
5. Zatim sama skida sve što treba (par minuta) i pita još tri stvari — za sve je odgovor **Enter** (= da):
   - da skine lokalni model (~1,6 GB, za rad bez interneta),
   - da napravi prečice na desktopu,
   - da podesiš brzo prepoznavanje preko interneta — tu te vodi korak po korak (vidi sledeći deo).

## Brzo prepoznavanje preko interneta (besplatni ključevi, ~5 minuta)

Treba ti **sopstveni** besplatan ključ — ne koristi tuđi (vidi dole zašto).

**ElevenLabs (glavni servis):**
1. Otvori https://elevenlabs.io → **Sign up** (može preko Google naloga). Plan ostavi **Free**.
2. Levo dole klikni **Developers**, pa gore karticu **API Keys**, pa **Create Key**.
3. Ime: `whisper`. Kod **Speech to Text** izaberi **Access**, sve ostalo ostavi **No Access**.
4. Klikni **Create Key** i kopiraj ključ (počinje sa `sk_`).

**Groq (rezerva kad potrošiš besplatne ElevenLabs sate):**
1. Otvori https://console.groq.com → prijavi se (može preko Google naloga).
2. Levo **API Keys** → **Create API Key** → ime `whisper` → kopiraj ključ (počinje sa `gsk_`).

Zatim dupli klik na **PODESI-KLJUCEVE.bat** (ili to uradi već tokom instalacije) i nalepi ključeve kad pita (desni klik u prozor = nalepi). Program odmah proveri da li ključ radi.

**Cena:** besplatno. ElevenLabs daje ~4,5 h snimka mesečno, posle toga automatski preuzima Groq (takođe besplatan), a bez interneta lokalni model. **Ne unosi karticu** ni na jednom sajtu — onda ništa ne može da se naplati.

**Zašto sopstveni ključ:** besplatni sati se troše po ključu. Ako više ljudi koristi isti ključ, potroše ih za par dana; a vlasnik ključa ne može da vidi ni da kontroliše ko ga koristi.

**Privatnost:** u ovom režimu snimak tvog glasa odlazi na server (ElevenLabs/Groq) da bi se pretvorio u tekst. Ako to ne želiš, preskoči ključeve — program radi lokalno.

## Svakodnevno korišćenje

1. Dupli klik na prečicu **WhisperWriter** na desktopu. Ikonica se pojavi pored sata; sačekaj da se otvori mali prozor, pa klikni **Start**.
2. Klikni mišem u polje gde želiš tekst.
3. Klikni **točkić miša** (ili `Ctrl+Alt+Space`), pričaj, pa klikni ponovo — tekst se sam otkuca.

Program radi u pozadini. Gasi se desnim klikom na ikonicu pored sata → **Exit**.

Ako želiš da vidiš šta program radi (status, brzinu, greške), pokreni **WhisperWriter.bat** umesto prečice — isti program, sa konzolom. Kod običnog starta te poruke idu u `whisperwriter.log`.

## Korisna podešavanja

Sva podešavanja su u fajlu `src\config.yaml` (otvori ga u Notepad-u). Najčešće izmene:

```yaml
language: sr          # jezik diktiranja: sr, en, de, fr... ili null = auto (prepoznaje sam)
activation_key: mouse_middle, ctrl+alt+space   # ili f9...
recording_mode: press_to_toggle   # ili hold_to_record (snima dok držiš taster)
use_api: true         # true = preko interneta, false = samo lokalno
ekavian: true         # vježbe -> vežbe, dio -> deo, poslije -> posle
remove_fillers: true  # briše poštapalice (ovaj, znači, kako se zove, eee...)
```

Posle izmene restartuj program.

## Ako tekst nije otkucan

Desni klik na ikonicu pored sata → **History (click = copy)** → tu su poslednje 3 izdiktirane rečenice. Klik na bilo koju je kopira celu, pa je nalepi sa **Ctrl+V**.

## Kada pogrešno čuje neku reč

Prečica **WhisperWriter ispravke** na desktopu otvara fajl `src\corrections.yaml`. Dodaj liniju:

```yaml
pogrešno: ispravno
```

npr. `kemit: commit`. Važi odmah za sledeću rečenicu, ne treba restart.

Imena ljudi, ekipa i stručne termine dodaj u spisak `_keyterms` u istom fajlu — onda ih servis preko interneta piše tačno.

## Problemi?

- **Ništa se ne dešava posle pokretanja** — sačekaj do minut; u lokalnom režimu model se učitava pre nego što se prozor pojavi.
- **Prečica ne radi** — proveri da li si kliknuo **Start** u glavnom prozoru.
- **Ključ ne radi** — pokreni **PODESI-KLJUCEVE.bat** ponovo; kod ElevenLabs proveri da ključ ima *Speech to Text: Access*.
- **Loše prepoznaje** — pričaj razgovetnije i bliže mikrofonu; dodaj problematične reči u `corrections.yaml`.

## Za radoznale

- Duže poruke se šalju deo po deo **dok pričaš**, pa posle puštanja čekaš samo poslednji deo.
- Statistika svakog diktiranja (trajanje, čekanje, koji servis je radio) upisuje se u `usage_stats.csv`.
- Poslednji snimak se čuva u `last_recording.wav` (samo lokalno, prepisuje se svaki put).

🇬🇧 English guide: [README.md](README.md)
