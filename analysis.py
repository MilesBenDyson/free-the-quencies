import json
from pathlib import Path
import numpy as np
from scipy.signal import get_window

# -----------------------------
# Persistenz: letzte Pfade merken
# -----------------------------
def _settings_file() -> Path:
    base = Path(__file__).resolve().parent
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
# Audio Analyse
# -----------------------------
def rms(signal: np.ndarray) -> float:
    signal = np.asarray(signal, dtype=np.float32)
    if signal.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(signal * signal)))


def rms_normalize(signal: np.ndarray, target_rms: float) -> np.ndarray:
    signal = np.asarray(signal, dtype=np.float32)
    cur = rms(signal)
    if cur <= 1e-12:
        return signal
    return signal * (target_rms / cur)


def averaged_spectrum(signal: np.ndarray, sr: int, fft_size: int = 4096, hop_size: int = 2048):
    """
    Liefert: freqs (Hz), spectrum_db (dBFS-ish, relativ)
    Robust auch bei kurzen Signalen.
    """
    signal = np.asarray(signal, dtype=np.float32)
    if signal.size < fft_size:
        # auf fft_size auffüllen
        pad = fft_size - signal.size
        signal = np.pad(signal, (0, pad), mode="constant")

    window = get_window("hann", fft_size)
    spectra = []

    # mind. 1 Frame auswerten
    last = max(1, (len(signal) - fft_size) // hop_size + 1)
    for k in range(last):
        i = k * hop_size
        frame = signal[i:i + fft_size]
        if frame.size < fft_size:
            frame = np.pad(frame, (0, fft_size - frame.size), mode="constant")
        frame = frame * window
        fft = np.fft.rfft(frame)
        spectra.append(np.abs(fft))

    spectra = np.asarray(spectra, dtype=np.float32)
    mean_spectrum = np.mean(spectra, axis=0)

    freqs = np.fft.rfftfreq(fft_size, 1.0 / sr)
    spectrum_db = 20.0 * np.log10(mean_spectrum + 1e-9)
    return freqs, spectrum_db


def third_octave_centers() -> np.ndarray:
    # Das ist deine "Soldano-Style" Post-EQ Frequenzliste
    return np.array([
        50, 63, 80, 100, 125, 160, 200, 250,
        315, 400, 500, 630, 800, 1000,
        1250, 1600, 2000, 2500, 3150,
        4000, 5000, 6300, 8000, 10000,
        12500, 16000
    ], dtype=float)


def spectrum_to_bands(freqs: np.ndarray, spec_db: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """
    Drittoktav-Bänder über Power-Mittelung.
    """
    mag = 10 ** (spec_db / 20.0)
    power = mag * mag

    edges = np.sqrt(centers[:-1] * centers[1:])
    lows = np.concatenate(([centers[0] / np.sqrt(centers[1] / centers[0])], edges))
    highs = np.concatenate((edges, [centers[-1] * np.sqrt(centers[-1] / centers[-2])]))

    band_db = []
    for lo, hi in zip(lows, highs):
        m = (freqs >= lo) & (freqs < hi)
        if not np.any(m):
            band_db.append(-120.0)
        else:
            avg_power = float(np.mean(power[m]))
            band_db.append(10.0 * np.log10(avg_power + 1e-12))

    return np.asarray(band_db, dtype=np.float32)


def analyze_difference(audio_a: np.ndarray, audio_b: np.ndarray, sr: int):
    """
    Ergebnis:
      freqs: centers
      bands_a: positive Pegel (0..)
      bands_b: positive Pegel (0..)
      diff_db: bands_b - bands_a (kann +/- sein)
    """
    # Lautheit angleichen (robust)
    ra = rms(audio_a)
    rb = rms(audio_b)
    target = (ra + rb) / 2.0 if (ra + rb) > 0 else 0.0

    audio_a = rms_normalize(audio_a, target)
    audio_b = rms_normalize(audio_b, target)

    freqs_a, spec_a = averaged_spectrum(audio_a, sr)
    freqs_b, spec_b = averaged_spectrum(audio_b, sr)

    centers = third_octave_centers()

    bands_a = spectrum_to_bands(freqs_a, spec_a, centers)
    bands_b = spectrum_to_bands(freqs_b, spec_b, centers)

    # in "nur positiv" umwandeln:
    # 0 = kein/geringster Energieinhalt im Band
    bands_a = bands_a - float(np.min(bands_a))
    bands_b = bands_b - float(np.min(bands_b))

    diff_db = bands_b - bands_a
    return centers, bands_a, bands_b, diff_db
