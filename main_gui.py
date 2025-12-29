import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout,
    QPushButton, QLineEdit, QLabel,
    QFileDialog, QTextEdit
)
from widgets.eq_band_row import EQBandRow
from widgets.eq_control import EQControl
from analysis import (
    load_settings, save_settings,
    compare_and_plot
)

class MainWindow(QMainWindow):

    def on_eq_changed(self):
        self.eq_bands.sort(key=lambda b: b["freq"])
        self.rebuild_eq_ui()

    def rebuild_eq_ui(self):
        # alte Widgets entfernen
        while self.eq_layout.count():
            item = self.eq_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # neue Widgets bauen
        for band in self.eq_bands:
            row = EQBandRow(band, self.on_eq_changed)
            self.eq_layout.addWidget(row)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("free-the-quencies – v1")
        self.resize(1200, 800)

        self.settings = load_settings()
        # ---------------- EQ-Datenmodell (Version 3.1) ----------------
        self.eq_bands = [
            {"freq": 65, "gain": 0.0},
            {"freq": 125, "gain": 0.0},
            {"freq": 250, "gain": 0.0},
            {"freq": 500, "gain": 0.0},
            {"freq": 1000, "gain": 0.0},
            {"freq": 2000, "gain": 0.0},
            {"freq": 4000, "gain": 0.0},
            {"freq": 8000, "gain": 0.0},
            {"freq": 16000, "gain": 0.0},
        ]

        central = QWidget()
        main_layout = QHBoxLayout()

        # ---------------- LEFT ----------------
        left = QVBoxLayout()

        self.path_a = QLineEdit(self.settings.get("last_path_a", ""))
        btn_a = QPushButton("Pfad A wählen")
        btn_a.clicked.connect(lambda: self.choose_file(self.path_a, "last_path_a"))

        self.path_b = QLineEdit(self.settings.get("last_path_b", ""))
        btn_b = QPushButton("Pfad B wählen")
        btn_b.clicked.connect(lambda: self.choose_file(self.path_b, "last_path_b"))

        left.addWidget(QLabel("Spur A"))
        left.addWidget(self.path_a)
        left.addWidget(btn_a)

        left.addSpacing(10)

        left.addWidget(QLabel("Spur B"))
        left.addWidget(self.path_b)
        left.addWidget(btn_b)

        left.addSpacing(20)

        left.addWidget(QLabel("Manueller EQ"))

        self.eq_layout = QVBoxLayout()

        for band in self.eq_bands:
            row = EQBandRow(band, self.on_eq_changed)
            self.eq_layout.addWidget(row)

        left.addLayout(self.eq_layout)

        self.analyze_btn = QPushButton("Analyse starten")
        left.addSpacing(20)
        left.addWidget(self.analyze_btn)

        left.addStretch()

        # ---------------- RIGHT ----------------
        right = QVBoxLayout()

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)

        right.addWidget(QLabel("Analyse-Ergebnis"))
        right.addWidget(self.result_text)

        # ---------------- FINAL ----------------
        main_layout.addLayout(left, 1)
        main_layout.addLayout(right, 2)

        central.setLayout(main_layout)
        self.setCentralWidget(central)

    def choose_file(self, line_edit, key):
        path, _ = QFileDialog.getOpenFileName(
            self, "Audiodatei wählen", "", "Audio (*.wav *.mp3 *.flac)"
        )
        if path:
            line_edit.setText(path)
            self.settings[key] = path
            save_settings(self.settings)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
