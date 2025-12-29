import json
from pathlib import Path


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
    p.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# -----------------------------
# Platzhalter für Analyse
# -----------------------------
def compare_and_plot(*args, **kwargs):
    """
    Platzhalter für Version 1.
    In Version 2 wird hier dein Audio-Analyse-Code eingebaut.
    """
    print("Analyse-Funktion wurde aufgerufen (noch ohne Audio-Logik).")
