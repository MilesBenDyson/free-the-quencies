import numpy as np
import librosa
import matplotlib.pyplot as plt
from scipy.signal import get_window

import json
from pathlib import Path


# -----------------------------
# Persistenz: letzte Pfade merken
# -----------------------------
def _settings_file() -> Path:
    base = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    return base / "audio_compare_settings.json"


def load_settings() -> dict:
    p = _settings_file()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(data: dict) -> None:
    p = _settings_file()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# -----------------------------
# Eingabe-Helfer: Pfade normalisieren
# -----------------------------
def normalize_path_input(s: str) -> str:
    r"""
    Entfernt führende/abschließende Leerzeichen und ignoriert äußere Anführungszeichen.
    Beispiele:
      "C:\foo\bar.wav" -> C:\foo\bar.wav
      'C:\foo\bar.wav' -> C:\foo\bar.wav
      ""C:\x.wav""     -> C:\x.wav
    """
    s = (s or "").strip()
    while (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    return s


# -----------------------------
# Robust: Audio-Datei abfragen + prüfen + laden
# -----------------------------
def ask_for_audio_file(
    prompt_label: str,
    default_path: str | None,
    target_sr: int = 44100
) -> tuple[str, np.ndarray, int]:
    """
    Gibt (path, audio, sr) zurück.
    Bei Fehlern kann der User neu eingeben oder abbrechen.
    Enter übernimmt default_path (falls vorhanden).
    Anführungszeichen um den Pfad werden ignoriert.
    """

    # default ebenfalls "säubern" (falls es mal mit Quotes gespeichert wurde)
    default_path = normalize_path_input(default_path) if default_path else None

    while True:
        if default_path:
            raw = input(f"{prompt_label} [Enter = letzter Pfad]\n> ")
            raw = normalize_path_input(raw)
            chosen = raw if raw else default_path
        else:
            chosen = normalize_path_input(input(f"{prompt_label}\n> "))

        if not chosen:
            print("Du hast keinen Pfad eingegeben.")
        else:
            p = Path(chosen)
            if not p.is_file():
                print(f"Pfad nicht gefunden oder keine Datei:\n{chosen}")
            else:
                # Versuch, Audio wirklich zu laden (Codec/Format/Permissions abfangen)
                try:
                    audio, sr = librosa.load(str(p), sr=target_sr, mono=True)
                    return str(p), audio, sr
                except Exception as e:
                    print(
                        "Datei existiert, aber konnte nicht als Audio geladen werden:\n"
                        f"{chosen}\nFehler: {e}"
                    )

        # Komfort: Enter zählt wie "E" (= nochmal versuchen)
        decision = input("Nochmal eingeben (E) oder abbrechen (A)? ").strip().lower()
        if decision == "a":
            raise SystemExit("Abgebrochen durch Nutzer.")
        # sonst -> Loop weiter


# -----------------------------
# RMS / Normalisierung
# -----------------------------
def rms(signal):
    return np.sqrt(np.mean(signal ** 2))


def rms_normalize(signal, target_rms):
    current_rms = rms(signal)
    if current_rms == 0:
        return signal
    gain = target_rms / current_rms
    return signal * gain


# -----------------------------
# FFT + Mittelung
# -----------------------------
def averaged_spectrum(signal, sr, fft_size=4096, hop_size=2048):
    window = get_window("hann", fft_size)
    spectra = []

    for i in range(0, len(signal) - fft_size, hop_size):
        frame = signal[i:i + fft_size] * window
        fft = np.fft.rfft(frame)
        spectra.append(np.abs(fft))

    spectra = np.array(spectra)
    mean_spectrum = np.mean(spectra, axis=0)

    freqs = np.fft.rfftfreq(fft_size, 1 / sr)
    spectrum_db = 20 * np.log10(mean_spectrum + 1e-9)
    return freqs, spectrum_db


def third_octave_centers():
    return np.array([
        50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630,
        800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300,
        8000, 10000, 12500, 16000
    ], dtype=float)


def spectrum_to_bands(freqs, spec_db, centers):
    mag = 10 ** (spec_db / 20.0)
    power = mag ** 2

    edges = np.sqrt(centers[:-1] * centers[1:])
    lows = np.concatenate(([centers[0] / np.sqrt(centers[1] / centers[0])], edges))
    highs = np.concatenate((edges, [centers[-1] * np.sqrt(centers[-1] / centers[-2])]))

    band_db = []
    for lo, hi in zip(lows, highs):
        m = (freqs >= lo) & (freqs < hi)
        if not np.any(m):
            band_db.append(-120.0)
        else:
            avg_power = np.mean(power[m])
            band_db.append(10 * np.log10(avg_power + 1e-12))
    return np.array(band_db)


# -----------------------------
# Vergleich/Plot
# -----------------------------
def compare_and_plot(audio_a, audio_b, sr):
    rms_a = rms(audio_a)
    rms_b = rms(audio_b)
    target_rms = (rms_a + rms_b) / 2

    audio_a_norm = rms_normalize(audio_a, target_rms)
    audio_b_norm = rms_normalize(audio_b, target_rms)

    print("RMS-Angleichung abgeschlossen")

    freqs_a, spec_a = averaged_spectrum(audio_a_norm, sr)
    freqs_b, spec_b = averaged_spectrum(audio_b_norm, sr)

    centers = third_octave_centers()

    bands_a = spectrum_to_bands(freqs_a, spec_a, centers)
    bands_b = spectrum_to_bands(freqs_b, spec_b, centers)

    # Formvergleich
    bands_a = bands_a - np.max(bands_a)
    bands_b = bands_b - np.max(bands_b)

    labels = []
    for f in centers:
        if f >= 1000:
            labels.append(f"{int(f/1000)}k" if f % 1000 == 0 else f"{f/1000:.1f}k")
        else:
            labels.append(str(int(f)))

    x = np.arange(len(centers))

    plt.figure(figsize=(12, 8))
    ymin = -90

    ax1 = plt.subplot(2, 1, 1)
    ax1.bar(x, bands_a - ymin, bottom=ymin, width=0.85)
    ax1.set_title("Spur A – Graphic EQ (Bänder 50 Hz–16 kHz)")
    ax1.set_ylabel("dB")
    ax1.set_ylim(-90, 0)
    ax1.grid(True, axis="y", which="both")

    ax2 = plt.subplot(2, 1, 2, sharex=ax1, sharey=ax1)
    ax2.bar(x, bands_b - ymin, bottom=ymin, width=0.85)
    ax2.set_title("Spur B – Graphic EQ (Bänder 50 Hz–16 kHz)")
    ax2.set_ylabel("dB")
    ax2.set_xlabel("Frequenzband")
    ax2.set_ylim(-90, 0)
    ax2.grid(True, axis="y", which="both")

    plt.xticks(x, labels, rotation=0)
    plt.tight_layout()
    plt.show()


# -----------------------------
# Main Loop (B neu laden / Neustart / Abbruch)
# -----------------------------
def main():
    print('Wenn du den letzten Pfad laden möchtest, drücke einfach enter, ansonsten gib deinen neuen Pfad ein.\n')

    settings = load_settings()

    while True:
        # ---- Spur A wählen (Neustart = hierhin zurück) ----
        last_a = settings.get("last_path_a")
        try:
            path_a, audio_a, sr = ask_for_audio_file("Pfad zu Spur A (z.B. riff.wav):", last_a)
        except SystemExit as e:
            print(e)
            return

        # Nur speichern, wenn wirklich geladen
        settings["last_path_a"] = path_a
        save_settings(settings)

        # ---- Spur B Loop (A bleibt gleich) ----
        while True:
            last_b = settings.get("last_path_b")
            try:
                path_b, audio_b, sr_b = ask_for_audio_file("Pfad zu Spur B (z.B. referenz.mp3):", last_b)
            except SystemExit as e:
                print(e)
                return

            settings["last_path_b"] = path_b
            save_settings(settings)

            compare_and_plot(audio_a, audio_b, sr)

            # Nach dem Vergleich: B neu / Neustart / Ende
            print("\nWas möchtest du als Nächstes?")
            print("1) Spur B neu laden (Spur A bleibt gleich)")
            print("2) Programm neustarten (Spur A und B neu wählen)")
            print("3) Beenden")

            choice = input("> ").strip()

            if choice == "1":
                continue  # zurück zur B-Auswahl (A bleibt)
            elif choice == "2":
                break     # raus aus B-Loop -> zurück zur A-Auswahl (Neustart)
            elif choice == "3":
                return
            else:
                print("Ungültige Eingabe. Bitte 1, 2 oder 3 wählen.")


if __name__ == "__main__":
    main()
