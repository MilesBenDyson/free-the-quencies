import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout,
    QPushButton, QLineEdit, QLabel,
    QFileDialog, QTextEdit
)

from widgets.eq_control import EQControl
from analysis import (
    load_settings, save_settings,
    compare_and_plot
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("free-the-quencies – v1")
        self.resize(1200, 800)

        self.settings = load_settings()

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

        self.eq_controls = []
        for freq in [50, 63, 80, 125, 250, 500, 1000, 2000, 4000, 8000]:
            eq = EQControl(f"{freq} Hz")
            self.eq_controls.append(eq)
            left.addWidget(eq)

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
