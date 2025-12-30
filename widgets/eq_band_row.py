from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import QLocale
from PyQt6.QtGui import QDoubleValidator


class EQBandRow(QWidget):
    """
    Eine Zeile:
    [ "500 Hz" ] [ Eingabefeld ]
    Schreibt direkt in store[str(freq)] als float.
    """

    def __init__(self, freq_hz: int, store: dict, parent=None):
        super().__init__(parent)
        self.freq_hz = int(freq_hz)
        self.store = store

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        lbl = QLabel(f"{self.freq_hz} Hz")
        lbl.setFixedWidth(70)
        layout.addWidget(lbl)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText("0.0")

        validator = QDoubleValidator(-24.0, 24.0, 3, self.edit)
        validator.setLocale(QLocale.system())
        self.edit.setValidator(validator)

        key = str(self.freq_hz)
        val = float(self.store.get(key, 0.0))
        self.edit.setText(f"{val:.3f}")

        self.edit.editingFinished.connect(self._commit)
        layout.addWidget(self.edit, 1)

    def _commit(self):
        key = str(self.freq_hz)
        txt = (self.edit.text() or "").strip().replace(",", ".")
        try:
            v = float(txt) if txt else 0.0
        except ValueError:
            v = 0.0

        # clamp
        v = max(-24.0, min(24.0, v))
        self.store[key] = v
        self.edit.setText(f"{v:.3f}")

    def set_value(self, value: float):
        value = float(value)
        value = max(-24.0, min(24.0, value))
        self.store[str(self.freq_hz)] = value
        self.edit.setText(f"{value:.3f}")
