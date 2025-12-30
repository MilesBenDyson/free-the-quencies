import sys
import json
from datetime import datetime
from pathlib import Path

import librosa

from PyQt6.QtCore import Qt, QLocale
from PyQt6.QtGui import QDoubleValidator, QIntValidator, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QFormLayout,
    QPushButton, QLineEdit, QLabel, QFileDialog, QTextEdit,
    QScrollArea, QGroupBox, QCheckBox,
    QToolButton, QComboBox,
    QGraphicsDropShadowEffect
)

from analysis import analyze_difference, load_settings, save_settings
from widgets.eq_plot import EQPlotWidget


# Default Frequenzen für Master Graphic EQ / Master Parametric EQ
MASTER_EQ_DEFAULT_FREQS = [65, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
MESA_5B = ["80", "240", "750", "2200", "6600"]


def _to_float(txt: str, default: float = 0.0) -> float:
    txt = (txt or "").strip().replace(",", ".")
    if not txt:
        return float(default)
    try:
        return float(txt)
    except ValueError:
        return float(default)


def _float_edit(default="0.0", lo=-24.0, hi=24.0, decimals=3):
    e = QLineEdit(default)
    v = QDoubleValidator(lo, hi, decimals, e)
    v.setLocale(QLocale.system())
    v.setNotation(QDoubleValidator.Notation.StandardNotation)
    e.setValidator(v)
    return e


def _int_edit(default="0", lo=0, hi=10):
    e = QLineEdit(default)
    v = QIntValidator(lo, hi, e)
    e.setValidator(v)
    return e


class CollapsibleSection(QWidget):
    """
    Ein einfacher auf-/zuklappbarer Bereich:
    Header mit Pfeil + darunter ein Content-Widget.
    """
    def __init__(self, title: str, expanded: bool = True, parent=None):
        super().__init__(parent)

        self.toggle = QToolButton()
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.toggle.setStyleSheet("QToolButton { font-weight: 600; padding: 6px; }")
        self.toggle.clicked.connect(self._on_toggled)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(10, 8, 10, 10)
        self.content_layout.setSpacing(8)
        self.content.setVisible(expanded)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.toggle)
        outer.addWidget(self.content)

        self.setStyleSheet("""
            CollapsibleSection {
                border: 1px solid #d6d6d6;
                border-radius: 10px;
            }
        """)

    def _on_toggled(self):
        expanded = self.toggle.isChecked()
        self.toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.content.setVisible(expanded)


class MasterGraphicBandRow(QWidget):
    """
    Eine Zeile: [Freq Hz] [Gain dB]  (beides editierbar)
    """
    def __init__(self, freq_hz: float, gain_db: float, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Freq"), 0)

        self.ed_freq = QLineEdit(f"{float(freq_hz):g}")
        vf = QDoubleValidator(1.0, 20000.0, 3, self.ed_freq)
        vf.setLocale(QLocale.system())
        vf.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.ed_freq.setValidator(vf)
        self.ed_freq.setFixedWidth(90)
        layout.addWidget(self.ed_freq, 0)

        layout.addWidget(QLabel("Hz"), 0)

        layout.addSpacing(10)
        layout.addWidget(QLabel("Gain"), 0)

        self.ed_gain = QLineEdit(f"{float(gain_db):g}")
        vg = QDoubleValidator(-24.0, 24.0, 3, self.ed_gain)
        vg.setLocale(QLocale.system())
        vg.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.ed_gain.setValidator(vg)
        self.ed_gain.setFixedWidth(80)
        layout.addWidget(self.ed_gain, 0)

        layout.addWidget(QLabel("dB"), 0)
        layout.addStretch(1)

    def get_values(self) -> dict:
        return {
            "freq_hz": _to_float(self.ed_freq.text(), 0.0),
            "gain_db": _to_float(self.ed_gain.text(), 0.0),
        }

    def set_values(self, freq_hz: float, gain_db: float):
        self.ed_freq.setText(f"{float(freq_hz):g}")
        self.ed_gain.setText(f"{float(gain_db):g}")


class MasterParametricBandRow(QWidget):
    """
    Eine Zeile: [Freq Hz] [Gain dB] [Type Peak/LoShelf/HiShelf] [Q]
    """
    SHAPES = ["Peak", "Low Shelf", "High Shelf"]

    def __init__(self, freq_hz: float, gain_db: float, shape: str = "Peak", q: float = 1.0, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Freq"), 0)
        self.ed_freq = QLineEdit(f"{float(freq_hz):g}")
        vf = QDoubleValidator(1.0, 20000.0, 3, self.ed_freq)
        vf.setLocale(QLocale.system())
        vf.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.ed_freq.setValidator(vf)
        self.ed_freq.setFixedWidth(90)
        layout.addWidget(self.ed_freq, 0)
        layout.addWidget(QLabel("Hz"), 0)

        layout.addSpacing(10)
        layout.addWidget(QLabel("Gain"), 0)
        self.ed_gain = QLineEdit(f"{float(gain_db):g}")
        vg = QDoubleValidator(-24.0, 24.0, 3, self.ed_gain)
        vg.setLocale(QLocale.system())
        vg.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.ed_gain.setValidator(vg)
        self.ed_gain.setFixedWidth(80)
        layout.addWidget(self.ed_gain, 0)
        layout.addWidget(QLabel("dB"), 0)

        layout.addSpacing(10)
        layout.addWidget(QLabel("Type"), 0)
        self.cb_shape = QComboBox()
        self.cb_shape.addItems(self.SHAPES)
        if shape in self.SHAPES:
            self.cb_shape.setCurrentText(shape)
        layout.addWidget(self.cb_shape, 0)

        layout.addSpacing(10)
        layout.addWidget(QLabel("Q"), 0)
        self.ed_q = QLineEdit(f"{float(q):g}")
        vq = QDoubleValidator(0.01, 50.0, 3, self.ed_q)
        vq.setLocale(QLocale.system())
        vq.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.ed_q.setValidator(vq)
        self.ed_q.setFixedWidth(70)
        layout.addWidget(self.ed_q, 0)

        layout.addStretch(1)

    def get_values(self) -> dict:
        return {
            "freq_hz": _to_float(self.ed_freq.text(), 0.0),
            "gain_db": _to_float(self.ed_gain.text(), 0.0),
            "shape": self.cb_shape.currentText(),
            "q": _to_float(self.ed_q.text(), 1.0),
        }

    def set_values(self, freq_hz: float, gain_db: float, shape: str, q: float):
        self.ed_freq.setText(f"{float(freq_hz):g}")
        self.ed_gain.setText(f"{float(gain_db):g}")
        if shape in self.SHAPES:
            self.cb_shape.setCurrentText(shape)
        self.ed_q.setText(f"{float(q):g}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("free-the-quencies")
        self.resize(1300, 850)

        self.settings = load_settings()

        # ---------- Datenmodell ----------
        self.preset = {
            "sound_name": "",
            "created": "",
            "source_files": {"path_a": "", "path_b": ""},
            "pedal": {
                "enabled": True,
                "name": "Tube Screamer",
                "gain": 0.0, "treble": 0.0, "middle": 0.0, "bass": 0.0,
                "contour": 0.0, "volume": 0.0
            },
            "amp": {
                "name": "Mesa Boogie Mark IIC+",
                "gain_1": 0.0, "gain_2": 0.0,
                "treble": 0.0, "middle": 0.0, "bass": 0.0,
                "presence": 0.0, "depth": 0.0, "master": 0.0
            },
            "graphic_eq": {
                "enabled": True,
                "type": "Mesa Boogie 5-Band",
                "bands_db": {k: 0.0 for k in MESA_5B}
            },
            "cab_ir": {
                "mic1": {"name": "SM57", "position": 4, "distance": 2, "level_db": -1.5},
                "mic2": {"name": "MD421", "position": 6, "distance": 3, "level_db": -3.0}
            },
            "master_graphic_eq": {
                "bands": [{"freq_hz": float(f), "gain_db": 0.0} for f in MASTER_EQ_DEFAULT_FREQS]
            },
            "master_parametric_eq": {
                "bands": [{"freq_hz": float(f), "gain_db": 0.0, "shape": "Peak", "q": 1.0} for f in MASTER_EQ_DEFAULT_FREQS]
            },
            # Snapshot für Plot/Ergebnis
            "analysis_snapshot": None
        }

        central = QWidget(self)
        root = QHBoxLayout(central)

        # ---------- LEFT: SCROLLAREA ----------
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)

        left_container = QWidget()
        left = QVBoxLayout(left_container)
        left.setContentsMargins(10, 10, 10, 10)
        left.setSpacing(10)

        # Pfade (mit Persistenz)
        self.path_a = QLineEdit(self.settings.get("last_path_a", ""))
        self.path_b = QLineEdit(self.settings.get("last_path_b", ""))

        btn_a = QPushButton("Spur A wählen")
        btn_b = QPushButton("Spur B wählen")
        btn_a.clicked.connect(lambda: self.pick(self.path_a, "last_path_a"))
        btn_b.clicked.connect(lambda: self.pick(self.path_b, "last_path_b"))

        left.addWidget(QLabel("Spur A"))
        left.addWidget(self.path_a)
        left.addWidget(btn_a)

        left.addWidget(QLabel("Spur B"))
        left.addWidget(self.path_b)
        left.addWidget(btn_b)

        # Analyse Button (oben, als klickbare Fläche hervorgehoben)
        self.btn_run = QPushButton("Analyse starten")
        self.btn_run.clicked.connect(self.run_analysis)
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setMinimumHeight(58)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #2d7dff;
                color: white;
                font-weight: 800;
                font-size: 16px;
                padding: 14px 16px;
                border-radius: 14px;
                border: 1px solid rgba(0, 0, 0, 0.18);
            }
            QPushButton:hover {
                background-color: #1f6cf0;
            }
            QPushButton:pressed {
                background-color: #155bd6;
                padding-top: 16px;
                padding-bottom: 12px;
            }
            QPushButton:disabled {
                background-color: #9bbcff;
                color: rgba(255, 255, 255, 0.85);
            }
        """)
        shadow = QGraphicsDropShadowEffect(self.btn_run)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.btn_run.setGraphicsEffect(shadow)
        left.addWidget(self.btn_run)

        # Soundname + Save/Load
        g_meta = QGroupBox("Preset")
        meta_form = QFormLayout(g_meta)
        self.ed_sound_name = QLineEdit("")
        self.ed_created = QLineEdit("")
        self.ed_created.setReadOnly(True)
        meta_form.addRow("Sound Name", self.ed_sound_name)
        meta_form.addRow("Created", self.ed_created)

        btn_save = QPushButton("Preset speichern (JSON)")
        btn_load = QPushButton("Preset laden (JSON)")
        btn_save.clicked.connect(self.save_preset_dialog)
        btn_load.clicked.connect(self.load_preset_dialog)

        meta_form.addRow(btn_save, btn_load)
        left.addWidget(g_meta)

        # ----------------------------
        # Pedal (aufklappbar)
        # ----------------------------
        sec_pedal = CollapsibleSection("Pedal", expanded=True)
        f_pedal = QFormLayout()
        self.cb_pedal = QCheckBox("enabled")
        self.cb_pedal.setChecked(True)
        self.ed_pedal_name = QLineEdit("Tube Screamer")
        self.ed_pedal_gain = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_pedal_treble = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_pedal_middle = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_pedal_bass = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_pedal_contour = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_pedal_volume = _float_edit("0.0", 0.0, 10.0, 3)

        f_pedal.addRow(self.cb_pedal, QLabel(""))
        f_pedal.addRow("name", self.ed_pedal_name)
        f_pedal.addRow("gain", self.ed_pedal_gain)
        f_pedal.addRow("treble", self.ed_pedal_treble)
        f_pedal.addRow("middle", self.ed_pedal_middle)
        f_pedal.addRow("bass", self.ed_pedal_bass)
        f_pedal.addRow("contour", self.ed_pedal_contour)
        f_pedal.addRow("volume", self.ed_pedal_volume)

        pedal_container = QWidget()
        pedal_container.setLayout(f_pedal)
        sec_pedal.content_layout.addWidget(pedal_container)
        left.addWidget(sec_pedal)

        # Amp (lassen wir als normalen Block – weniger Umbau)
        g_amp = QGroupBox("Amp")
        f_amp = QFormLayout(g_amp)
        self.ed_amp_name = QLineEdit("Mesa Boogie Mark IIC+")
        self.ed_amp_g1 = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_amp_g2 = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_amp_treble = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_amp_middle = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_amp_bass = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_amp_presence = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_amp_depth = _float_edit("0.0", 0.0, 10.0, 3)
        self.ed_amp_master = _float_edit("0.0", 0.0, 10.0, 3)

        f_amp.addRow("name", self.ed_amp_name)
        f_amp.addRow("gain_1", self.ed_amp_g1)
        f_amp.addRow("gain_2", self.ed_amp_g2)
        f_amp.addRow("treble", self.ed_amp_treble)
        f_amp.addRow("middle", self.ed_amp_middle)
        f_amp.addRow("bass", self.ed_amp_bass)
        f_amp.addRow("presence", self.ed_amp_presence)
        f_amp.addRow("depth", self.ed_amp_depth)
        f_amp.addRow("master", self.ed_amp_master)
        left.addWidget(g_amp)

        # ----------------------------
        # Graphic EQ (Mesa 5-Band) (aufklappbar)
        # ----------------------------
        sec_geq = CollapsibleSection("Graphic EQ (Mesa 5-Band)", expanded=True)
        f_geq = QFormLayout()
        self.cb_geq = QCheckBox("enabled")
        self.cb_geq.setChecked(True)
        self.ed_geq_type = QLineEdit("Mesa Boogie 5-Band")
        self.ed_geq_type.setReadOnly(True)
        f_geq.addRow(self.cb_geq, QLabel(""))
        f_geq.addRow("type", self.ed_geq_type)

        self.geq_edits = {}
        for k in MESA_5B:
            e = _float_edit("0.0", -12.0, 12.0, 3)
            self.geq_edits[k] = e
            f_geq.addRow(f"{k} Hz", e)

        geq_container = QWidget()
        geq_container.setLayout(f_geq)
        sec_geq.content_layout.addWidget(geq_container)
        left.addWidget(sec_geq)

        # ----------------------------
        # Cab / IR (aufklappbar)
        # ----------------------------
        sec_cab = CollapsibleSection("Cab / IR", expanded=True)
        f_cab = QFormLayout()

        self.ed_m1_name = QLineEdit("SM57")
        self.ed_m1_pos = _int_edit("4", 0, 10)
        self.ed_m1_dist = _int_edit("2", 0, 10)
        self.ed_m1_lvl = _float_edit("-1.5", -24.0, 12.0, 3)

        self.ed_m2_name = QLineEdit("MD421")
        self.ed_m2_pos = _int_edit("6", 0, 10)
        self.ed_m2_dist = _int_edit("3", 0, 10)
        self.ed_m2_lvl = _float_edit("-3.0", -24.0, 12.0, 3)

        f_cab.addRow("mic1 name", self.ed_m1_name)
        f_cab.addRow("mic1 position", self.ed_m1_pos)
        f_cab.addRow("mic1 distance", self.ed_m1_dist)
        f_cab.addRow("mic1 level_db", self.ed_m1_lvl)
        f_cab.addRow(QLabel(""), QLabel(""))
        f_cab.addRow("mic2 name", self.ed_m2_name)
        f_cab.addRow("mic2 position", self.ed_m2_pos)
        f_cab.addRow("mic2 distance", self.ed_m2_dist)
        f_cab.addRow("mic2 level_db", self.ed_m2_lvl)

        cab_container = QWidget()
        cab_container.setLayout(f_cab)
        sec_cab.content_layout.addWidget(cab_container)
        left.addWidget(sec_cab)

        # ----------------------------
        # Master Graphic EQ (aufklappbar, variabel viele Bänder)
        # ----------------------------
        sec_mgeq = CollapsibleSection("Master Graphic EQ", expanded=True)

        btn_row_mgeq = QWidget()
        bl_mgeq = QHBoxLayout(btn_row_mgeq)
        bl_mgeq.setContentsMargins(0, 0, 0, 0)
        self.btn_mgeq_add = QPushButton("+ Band")
        self.btn_mgeq_del = QPushButton("− Band")
        self.btn_mgeq_add.clicked.connect(self.mgeq_add_band)
        self.btn_mgeq_del.clicked.connect(self.mgeq_remove_band)
        bl_mgeq.addWidget(self.btn_mgeq_add)
        bl_mgeq.addWidget(self.btn_mgeq_del)
        bl_mgeq.addStretch(1)

        sec_mgeq.content_layout.addWidget(btn_row_mgeq)

        self.mgeq_scroll = QScrollArea()
        self.mgeq_scroll.setWidgetResizable(True)
        self.mgeq_box = QWidget()
        self.mgeq_layout = QVBoxLayout(self.mgeq_box)
        self.mgeq_layout.setContentsMargins(0, 0, 0, 0)
        self.mgeq_layout.setSpacing(6)
        self.mgeq_rows = []

        self.mgeq_scroll.setWidget(self.mgeq_box)
        self.mgeq_scroll.setMinimumHeight(200)
        sec_mgeq.content_layout.addWidget(self.mgeq_scroll)

        left.addWidget(sec_mgeq)

        # ----------------------------
        # Master Parametic EQ (aufklappbar, 9 Bands als Start)
        # ----------------------------
        sec_mpeq = CollapsibleSection("Master Parametic EQ", expanded=False)

        btn_row_mpeq = QWidget()
        bl_mpeq = QHBoxLayout(btn_row_mpeq)
        bl_mpeq.setContentsMargins(0, 0, 0, 0)
        self.btn_mpeq_add = QPushButton("+ Band")
        self.btn_mpeq_del = QPushButton("− Band")
        self.btn_mpeq_add.clicked.connect(self.mpeq_add_band)
        self.btn_mpeq_del.clicked.connect(self.mpeq_remove_band)
        bl_mpeq.addWidget(self.btn_mpeq_add)
        bl_mpeq.addWidget(self.btn_mpeq_del)
        bl_mpeq.addStretch(1)

        sec_mpeq.content_layout.addWidget(btn_row_mpeq)

        self.mpeq_scroll = QScrollArea()
        self.mpeq_scroll.setWidgetResizable(True)
        self.mpeq_box = QWidget()
        self.mpeq_layout = QVBoxLayout(self.mpeq_box)
        self.mpeq_layout.setContentsMargins(0, 0, 0, 0)
        self.mpeq_layout.setSpacing(6)
        self.mpeq_rows = []

        self.mpeq_scroll.setWidget(self.mpeq_box)
        self.mpeq_scroll.setMinimumHeight(240)
        sec_mpeq.content_layout.addWidget(self.mpeq_scroll)

        left.addWidget(sec_mpeq)

        left.addStretch(1)

        left_scroll.setWidget(left_container)

        # ---------- RIGHT ----------
        right = QVBoxLayout()
        self.eq_plot = EQPlotWidget()
        self.text = QTextEdit()
        self.text.setReadOnly(True)

        right.addWidget(self.eq_plot, 3)
        right.addWidget(self.text, 1)

        root.addWidget(left_scroll, 1)
        root.addLayout(right, 2)

        self.setCentralWidget(central)

        # Initiale Rows nach Default
        self._rebuild_mgeq_rows(self.preset["master_graphic_eq"]["bands"])
        self._rebuild_mpeq_rows(self.preset["master_parametric_eq"]["bands"])

    # ---------------------------
    # Dynamische Rows (Master EQs)
    # ---------------------------
    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _rebuild_mgeq_rows(self, bands: list[dict]):
        self._clear_layout(self.mgeq_layout)
        self.mgeq_rows = []
        for b in bands:
            row = MasterGraphicBandRow(b.get("freq_hz", 0.0), b.get("gain_db", 0.0))
            self.mgeq_layout.addWidget(row)
            self.mgeq_rows.append(row)
        self.mgeq_layout.addStretch(1)

    def _rebuild_mpeq_rows(self, bands: list[dict]):
        self._clear_layout(self.mpeq_layout)
        self.mpeq_rows = []
        for b in bands:
            row = MasterParametricBandRow(
                b.get("freq_hz", 0.0),
                b.get("gain_db", 0.0),
                b.get("shape", "Peak"),
                b.get("q", 1.0)
            )
            self.mpeq_layout.addWidget(row)
            self.mpeq_rows.append(row)
        self.mpeq_layout.addStretch(1)

    def mgeq_add_band(self):
        row = MasterGraphicBandRow(1000.0, 0.0)
        # vor dem Stretch einsetzen
        self.mgeq_layout.insertWidget(max(0, self.mgeq_layout.count() - 1), row)
        self.mgeq_rows.append(row)

    def mgeq_remove_band(self):
        if not self.mgeq_rows:
            return
        row = self.mgeq_rows.pop()
        row.setParent(None)
        row.deleteLater()

    def mpeq_add_band(self):
        row = MasterParametricBandRow(1000.0, 0.0, "Peak", 1.0)
        self.mpeq_layout.insertWidget(max(0, self.mpeq_layout.count() - 1), row)
        self.mpeq_rows.append(row)

    def mpeq_remove_band(self):
        if not self.mpeq_rows:
            return
        row = self.mpeq_rows.pop()
        row.setParent(None)
        row.deleteLater()

    # ---------------------------
    # Pfad wählen + persistieren
    # ---------------------------
    def pick(self, field: QLineEdit, key: str):
        path, _ = QFileDialog.getOpenFileName(self, "Audio wählen", "", "Audio (*.wav *.mp3 *.flac)")
        if path:
            field.setText(path)
            self.settings[key] = path
            save_settings(self.settings)

    # ---------------------------
    # Preset sammeln / anwenden
    # ---------------------------
    def _format_diff_html(self, freqs, diff_db):
        """Erstellt farbige HTML-Ausgabe für die Δ dB-Liste.

        Regeln:
        - |Δ| <= 0.5 dB -> grün
        - Δ > 0.5 dB -> gelb
        - Δ < -0.5 dB -> rot
        """
        # Farben: gut lesbar im Dark-Theme
        COL_GREEN = "#3DDC84"
        COL_YELLOW = "#FFD54F"
        COL_RED = "#FF5C5C"

        lines = []
        for f, d in zip(freqs, diff_db):
            if abs(d) <= 0.5:
                col = COL_GREEN
                mark = "✔"
            elif d > 0.5:
                col = COL_YELLOW
                mark = ""
            else:
                col = COL_RED
                mark = ""

            # Frequenzanzeige: integer (Hz)
            f_txt = f"{int(float(f)):>5} Hz : Δ "
            d_txt = f"{float(d):+0.2f} dB"
            lines.append(f"{f_txt}<span style='color:{col}; font-weight:700;'>{d_txt}</span> {mark}")

        html = (
            "<pre style=\"margin:0; font-family:Consolas,'Courier New',monospace; font-size:12px;\">\n"
            + "\n".join(lines)
            + "\n</pre>"
        )
        return html


    def _collect_preset_from_ui(self):
        self.preset["sound_name"] = self.ed_sound_name.text().strip()
        self.preset["created"] = self.ed_created.text().strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.preset["source_files"]["path_a"] = self.path_a.text().strip()
        self.preset["source_files"]["path_b"] = self.path_b.text().strip()

        self.preset["pedal"]["enabled"] = self.cb_pedal.isChecked()
        self.preset["pedal"]["name"] = self.ed_pedal_name.text().strip()
        self.preset["pedal"]["gain"] = _to_float(self.ed_pedal_gain.text(), 0.0)
        self.preset["pedal"]["treble"] = _to_float(self.ed_pedal_treble.text(), 0.0)
        self.preset["pedal"]["middle"] = _to_float(self.ed_pedal_middle.text(), 0.0)
        self.preset["pedal"]["bass"] = _to_float(self.ed_pedal_bass.text(), 0.0)
        self.preset["pedal"]["contour"] = _to_float(self.ed_pedal_contour.text(), 0.0)
        self.preset["pedal"]["volume"] = _to_float(self.ed_pedal_volume.text(), 0.0)

        self.preset["amp"]["name"] = self.ed_amp_name.text().strip()
        self.preset["amp"]["gain_1"] = _to_float(self.ed_amp_g1.text(), 0.0)
        self.preset["amp"]["gain_2"] = _to_float(self.ed_amp_g2.text(), 0.0)
        self.preset["amp"]["treble"] = _to_float(self.ed_amp_treble.text(), 0.0)
        self.preset["amp"]["middle"] = _to_float(self.ed_amp_middle.text(), 0.0)
        self.preset["amp"]["bass"] = _to_float(self.ed_amp_bass.text(), 0.0)
        self.preset["amp"]["presence"] = _to_float(self.ed_amp_presence.text(), 0.0)
        self.preset["amp"]["depth"] = _to_float(self.ed_amp_depth.text(), 0.0)
        self.preset["amp"]["master"] = _to_float(self.ed_amp_master.text(), 0.0)

        self.preset["graphic_eq"]["enabled"] = self.cb_geq.isChecked()
        self.preset["graphic_eq"]["type"] = self.ed_geq_type.text().strip()
        for k, e in self.geq_edits.items():
            self.preset["graphic_eq"]["bands_db"][k] = _to_float(e.text(), 0.0)

        self.preset["cab_ir"]["mic1"]["name"] = self.ed_m1_name.text().strip()
        self.preset["cab_ir"]["mic1"]["position"] = int(_to_float(self.ed_m1_pos.text(), 0))
        self.preset["cab_ir"]["mic1"]["distance"] = int(_to_float(self.ed_m1_dist.text(), 0))
        self.preset["cab_ir"]["mic1"]["level_db"] = _to_float(self.ed_m1_lvl.text(), 0.0)

        self.preset["cab_ir"]["mic2"]["name"] = self.ed_m2_name.text().strip()
        self.preset["cab_ir"]["mic2"]["position"] = int(_to_float(self.ed_m2_pos.text(), 0))
        self.preset["cab_ir"]["mic2"]["distance"] = int(_to_float(self.ed_m2_dist.text(), 0))
        self.preset["cab_ir"]["mic2"]["level_db"] = _to_float(self.ed_m2_lvl.text(), 0.0)

        # Master Graphic EQ
        bands = []
        for row in self.mgeq_rows:
            b = row.get_values()
            # simple sanity: skip empty/invalid
            if b["freq_hz"] > 0:
                bands.append(b)
        self.preset["master_graphic_eq"]["bands"] = bands

        # Master Parametic EQ
        pbands = []
        for row in self.mpeq_rows:
            b = row.get_values()
            if b["freq_hz"] > 0:
                pbands.append(b)
        self.preset["master_parametric_eq"]["bands"] = pbands

        # analysis_snapshot bleibt wie es ist (wird beim Analysieren gesetzt)

    def _apply_preset_to_ui(self, preset: dict):
        # Backward-Kompatibilität: alte Keys abfangen
        if "master_graphic_eq" not in preset:
            # altes manual_eq (dict) -> in Liste umwandeln
            me = preset.get("manual_eq", {})
            if isinstance(me, dict) and me:
                bands = []
                for k, v in me.items():
                    bands.append({"freq_hz": _to_float(str(k), 0.0), "gain_db": _to_float(str(v), 0.0)})
                preset["master_graphic_eq"] = {"bands": bands}
            else:
                preset["master_graphic_eq"] = {"bands": [{"freq_hz": float(f), "gain_db": 0.0} for f in MASTER_EQ_DEFAULT_FREQS]}

        if "master_parametric_eq" not in preset:
            preset["master_parametric_eq"] = {"bands": [{"freq_hz": float(f), "gain_db": 0.0, "shape": "Peak", "q": 1.0} for f in MASTER_EQ_DEFAULT_FREQS]}

        # post_eq wird bewusst ignoriert, falls alte Presets es noch enthalten

        self.preset = preset

        self.ed_sound_name.setText(preset.get("sound_name", ""))
        self.ed_created.setText(preset.get("created", ""))

        sf = preset.get("source_files", {})
        self.path_a.setText(sf.get("path_a", ""))
        self.path_b.setText(sf.get("path_b", ""))

        ped = preset.get("pedal", {})
        self.cb_pedal.setChecked(bool(ped.get("enabled", True)))
        self.ed_pedal_name.setText(str(ped.get("name", "")))
        self.ed_pedal_gain.setText(str(ped.get("gain", 0.0)))
        self.ed_pedal_treble.setText(str(ped.get("treble", 0.0)))
        self.ed_pedal_middle.setText(str(ped.get("middle", 0.0)))
        self.ed_pedal_bass.setText(str(ped.get("bass", 0.0)))
        self.ed_pedal_contour.setText(str(ped.get("contour", 0.0)))
        self.ed_pedal_volume.setText(str(ped.get("volume", 0.0)))

        amp = preset.get("amp", {})
        self.ed_amp_name.setText(str(amp.get("name", "")))
        self.ed_amp_g1.setText(str(amp.get("gain_1", 0.0)))
        self.ed_amp_g2.setText(str(amp.get("gain_2", 0.0)))
        self.ed_amp_treble.setText(str(amp.get("treble", 0.0)))
        self.ed_amp_middle.setText(str(amp.get("middle", 0.0)))
        self.ed_amp_bass.setText(str(amp.get("bass", 0.0)))
        self.ed_amp_presence.setText(str(amp.get("presence", 0.0)))
        self.ed_amp_depth.setText(str(amp.get("depth", 0.0)))
        self.ed_amp_master.setText(str(amp.get("master", 0.0)))

        geq = preset.get("graphic_eq", {})
        self.cb_geq.setChecked(bool(geq.get("enabled", True)))
        bands = geq.get("bands_db", {})
        for k, e in self.geq_edits.items():
            e.setText(str(bands.get(k, 0.0)))

        cab = preset.get("cab_ir", {})
        m1 = cab.get("mic1", {})
        m2 = cab.get("mic2", {})
        self.ed_m1_name.setText(str(m1.get("name", "")))
        self.ed_m1_pos.setText(str(m1.get("position", 0)))
        self.ed_m1_dist.setText(str(m1.get("distance", 0)))
        self.ed_m1_lvl.setText(str(m1.get("level_db", 0.0)))
        self.ed_m2_name.setText(str(m2.get("name", "")))
        self.ed_m2_pos.setText(str(m2.get("position", 0)))
        self.ed_m2_dist.setText(str(m2.get("distance", 0)))
        self.ed_m2_lvl.setText(str(m2.get("level_db", 0.0)))

        # Master EQ Rows rebuild
        mgeq = preset.get("master_graphic_eq", {})
        self._rebuild_mgeq_rows(list(mgeq.get("bands", [])) or [{"freq_hz": float(f), "gain_db": 0.0} for f in MASTER_EQ_DEFAULT_FREQS])

        mpeq = preset.get("master_parametric_eq", {})
        self._rebuild_mpeq_rows(list(mpeq.get("bands", [])) or [{"freq_hz": float(f), "gain_db": 0.0, "shape": "Peak", "q": 1.0} for f in MASTER_EQ_DEFAULT_FREQS])

        # wenn Snapshot vorhanden -> Plot sofort zeigen
        snap = preset.get("analysis_snapshot")
        if snap:
            freqs = snap.get("freqs", [])
            ba = snap.get("bands_a", [])
            bb = snap.get("bands_b", [])
            diff = snap.get("diff_db", [])
            if freqs and ba and bb and diff:
                self.eq_plot.update_plot(freqs, ba, bb, diff)
                # Snapshot: wenn möglich erneut farbig rendern
            try:
                freqs = snap.get("freqs", [])
                diff = snap.get("diff_db", [])
                if freqs and diff and len(freqs) == len(diff):
                    self.text.setHtml(self._format_diff_html(freqs, diff))
                else:
                    self.text.setText("\n".join(snap.get("text_lines", [])))
            except Exception:
                self.text.setText("\n".join(snap.get("text_lines", [])))

    # ---------------------------
    # Preset speichern/laden
    # ---------------------------
    def save_preset_dialog(self):
        self._collect_preset_from_ui()

        # created automatisch setzen, falls leer
        if not self.preset["created"]:
            self.preset["created"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.ed_created.setText(self.preset["created"])

        start_dir = self.settings.get("last_preset_dir", "")
        path, _ = QFileDialog.getSaveFileName(self, "Preset speichern", start_dir, "JSON (*.json)")
        if not path:
            return

        p = Path(path)
        self.settings["last_preset_dir"] = str(p.parent)
        save_settings(self.settings)

        try:
            p.write_text(json.dumps(self.preset, ensure_ascii=False, indent=2), encoding="utf-8")
            self.text.append("\nPreset gespeichert ✅")
        except Exception as e:
            self.text.setText(f"Fehler beim Speichern:\n{e}")

    def load_preset_dialog(self):
        start_dir = self.settings.get("last_preset_dir", "")
        path, _ = QFileDialog.getOpenFileName(self, "Preset laden", start_dir, "JSON (*.json)")
        if not path:
            return

        p = Path(path)
        self.settings["last_preset_dir"] = str(p.parent)
        save_settings(self.settings)

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Preset ist kein JSON-Objekt.")

            # Wenn im Preset kein Sound-Name gespeichert ist, nutze den Dateinamen
            if not str(data.get("sound_name", "")).strip():
                data["sound_name"] = p.stem
            self._apply_preset_to_ui(data)
            self.text.append("\nPreset geladen ✅")
        except Exception as e:
            self.text.setText(f"Fehler beim Laden:\n{e}")

    # ---------------------------
    # Analyse
    # ---------------------------
    def run_analysis(self):
        a = self.path_a.text().strip()
        b = self.path_b.text().strip()

        if not a or not b:
            self.text.setText("Bitte Spur A und Spur B auswählen.")
            return

        try:
            self.btn_run.setEnabled(False)

            audio_a, sr = librosa.load(a, sr=44100, mono=True)
            audio_b, _ = librosa.load(b, sr=44100, mono=True)

            freqs, ba, bb, diff = analyze_difference(audio_a, audio_b, sr)

            self.eq_plot.update_plot(freqs, ba, bb, diff)

            # Farbcodierte Δ-Liste (grün: |Δ|<=0.5 / gelb: positiv / rot: negativ)
            html = self._format_diff_html(freqs, diff)
            # Zusätzlich plain lines im Snapshot behalten (für Kompatibilität)
            lines = []
            for f, d in zip(freqs, diff):
                mark = "✔" if abs(d) <= 0.5 else ""
                lines.append(f"{int(float(f)):>5} Hz : Δ {float(d):+.2f} dB {mark}")

            self.text.setHtml(html)

            # Snapshot in preset
            self._collect_preset_from_ui()
            self.preset["analysis_snapshot"] = {
                "freqs": [float(x) for x in freqs],
                "bands_a": [float(x) for x in ba],
                "bands_b": [float(x) for x in bb],
                "diff_db": [float(x) for x in diff],
                "text_lines": lines
            }

        except Exception as e:
            self.text.setText(f"Fehler bei Analyse:\n{e}")
        finally:
            self.btn_run.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
