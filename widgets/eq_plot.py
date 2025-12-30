from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np


class EQPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.fig = Figure(figsize=(6, 4))
        self.canvas = FigureCanvasQTAgg(self.fig)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.ax = self.fig.add_subplot(111)

    def update_plot(self, freqs, bands_a, bands_b, diff_db, match_threshold_db=0.5):
        self.ax.clear()

        freqs = np.asarray(freqs, dtype=float)
        bands_a = np.asarray(bands_a, dtype=float)
        bands_b = np.asarray(bands_b, dtype=float)
        diff_db = np.asarray(diff_db, dtype=float)

        x = np.arange(len(freqs))
        width = 0.38

        bars_a = self.ax.bar(
            x - width / 2,
            bands_a,
            width,
            color="dodgerblue",
            alpha=0.9,
            label="Spur A"
        )

        bars_b = self.ax.bar(
            x + width / 2,
            bands_b,
            width,
            color="purple",
            alpha=0.9,
            label="Spur B"
        )

        # Match-Spitzen (grün)
        tip_height = max(0.6, 0.02 * max(float(bands_a.max()), float(bands_b.max()), 1.0))

        for bar_a, bar_b, d in zip(bars_a, bars_b, diff_db):
            if abs(d) <= match_threshold_db:
                for bar in (bar_a, bar_b):
                    h = float(bar.get_height())
                    if h <= 0:
                        continue
                    self.ax.bar(
                        bar.get_x(),
                        min(tip_height, h),
                        bar.get_width(),
                        bottom=h - min(tip_height, h),
                        color="green",
                        alpha=0.95,
                        zorder=5
                    )

        self.ax.set_title("Bandvergleich (Spur A vs Spur B)")
        self.ax.set_xlabel("Frequenz (Hz)")
        self.ax.set_ylabel("Pegel (dB)")

        ymax = max(float(bands_a.max()), float(bands_b.max()), 1.0)
        self.ax.set_ylim(0, ymax * 1.15)

        self.ax.set_xticks(x)
        self.ax.set_xticklabels(
            [f"{int(f)}" if f < 1000 else f"{f/1000:.1f}k" for f in freqs],
            rotation=45
        )

        self.ax.grid(True, axis="y", linestyle="--", alpha=0.35)
        self.ax.legend()

        self.canvas.draw()
