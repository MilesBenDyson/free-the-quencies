from PyQt6.QtWidgets import (
    QWidget, QSpinBox, QHBoxLayout
)
from widgets.eq_control import EQControl


class EQBandRow(QWidget):
    def __init__(self, band_data, on_change_callback):
        super().__init__()

        self.band_data = band_data
        self.on_change = on_change_callback

        # Frequenz-Eingabe
        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(20, 20000)
        self.freq_spin.setValue(band_data["freq"])
        self.freq_spin.setSuffix(" Hz")
        self.freq_spin.setFixedWidth(90)

        # Gain-EQ
        self.eq = EQControl("")
        self.eq.set_value(band_data["gain"])

        # Signale verbinden
        self.freq_spin.valueChanged.connect(self._freq_changed)
        self.eq.spin.valueChanged.connect(self._gain_changed)

        layout = QHBoxLayout()
        layout.addWidget(self.freq_spin)
        layout.addWidget(self.eq)
        self.setLayout(layout)

    def _freq_changed(self, value):
        self.band_data["freq"] = value
        self.on_change()

    def _gain_changed(self, value):
        self.band_data["gain"] = value
        self.on_change()
