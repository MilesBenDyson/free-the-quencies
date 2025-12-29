from PyQt6.QtWidgets import (
    QWidget, QLabel, QSlider, QDoubleSpinBox, QHBoxLayout
)
from PyQt6.QtCore import Qt


class EQControl(QWidget):
    def __init__(self, label_text, min_db=-12.0, max_db=12.0, step=0.1):
        super().__init__()

        self.label = QLabel(label_text)
        self.label.setFixedWidth(60)

        # Slider arbeitet intern mit *10
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(min_db * 10))
        self.slider.setMaximum(int(max_db * 10))
        self.slider.setSingleStep(1)

        self.spin = QDoubleSpinBox()
        self.spin.setRange(min_db, max_db)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(1)
        self.spin.setSuffix(" dB")
        self.spin.setFixedWidth(80)

        # Synchronisation
        self.slider.valueChanged.connect(
            lambda v: self.spin.setValue(v / 10)
        )
        self.spin.valueChanged.connect(
            lambda v: self.slider.setValue(int(v * 10))
        )

        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addWidget(self.spin)
        self.setLayout(layout)

    def value(self):
        return self.spin.value()

    def set_value(self, db):
        self.spin.setValue(db)
