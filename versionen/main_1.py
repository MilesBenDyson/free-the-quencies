import numpy as np
import librosa
import matplotlib.pyplot as plt
from scipy.signal import get_window

# -----------------------------
# Audio laden & vorbereiten
# -----------------------------
def load_audio(path, target_sr=44100):
    audio, sr = librosa.load(path, sr=target_sr, mono=True)
    return audio, sr

# -----------------------------
# RMS berechnen
# -----------------------------
def rms(signal):
    return np.sqrt(np.mean(signal ** 2))

# -----------------------------
# RMS-Normalisierung
# -----------------------------
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
        frame = signal[i:i + fft_size]
        frame = frame * window

        fft = np.fft.rfft(frame)
        mag = np.abs(fft)
        spectra.append(mag)

    spectra = np.array(spectra)
    mean_spectrum = np.mean(spectra, axis=0)

    freqs = np.fft.rfftfreq(fft_size, 1 / sr)
    spectrum_db = 20 * np.log10(mean_spectrum + 1e-9)

    return freqs, spectrum_db

def third_octave_centers(fmin=50, fmax=16000):
    # 1/3 Oktav – praxisnahe Center-Frequenzen (ähnlich EQ-Bändern)
    return np.array([
        50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630,
        800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300,
        8000, 10000, 12500, 16000
    ], dtype=float)

def spectrum_to_bands(freqs, spec_db, centers):
    """
    Mappt ein Spektrum auf Bandwerte (Balken).
    Wir mitteln im Power-Bereich (stabiler), dann zurück nach dB.
    """
    # dB -> Magnitude -> Power
    mag = 10 ** (spec_db / 20.0)
    power = mag ** 2

    # Bandgrenzen als geometrische Mitte zwischen benachbarten Centers
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
    return np.array(band_db), lows, highs


# -----------------------------
# Dateien auswählen
# -----------------------------
file_a = input("Pfad zu Spur A (z.B. riff.wav): ")
file_b = input("Pfad zu Spur B (z.B. referenz.mp3): ")

# -----------------------------
# Laden
# -----------------------------
audio_a, sr = load_audio(file_a)
audio_b, _  = load_audio(file_b)

# -----------------------------
# RMS-Angleichung
# -----------------------------
rms_a = rms(audio_a)
rms_b = rms(audio_b)
target_rms = (rms_a + rms_b) / 2

audio_a_norm = rms_normalize(audio_a, target_rms)
audio_b_norm = rms_normalize(audio_b, target_rms)

print("RMS-Angleichung abgeschlossen")

# -----------------------------
# Analyse
# -----------------------------
freqs_a, spec_a = averaged_spectrum(audio_a_norm, sr)
freqs_b, spec_b = averaged_spectrum(audio_b_norm, sr)

# Frequenzbereich begrenzen
mask = (freqs_a >= 50) & (freqs_a <= 16000)

# -----------------------------
# Plot als "Grafischer Equalizer"
# -----------------------------
centers = third_octave_centers(50, 16000)

bands_a, _, _ = spectrum_to_bands(freqs_a, spec_a, centers)
bands_b, _, _ = spectrum_to_bands(freqs_b, spec_b, centers)

# optional: "Formvergleich" statt absolute Pegel
# (macht Unterschiede besser sichtbar)
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

