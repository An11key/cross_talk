from __future__ import annotations

import numpy as np
import pandas as pd
import pyqtgraph as pg


def plot_dataframe(plot_widget: pg.PlotWidget, data: pd.DataFrame) -> None:
    plot_widget.clear()
    plot_widget.enableAutoRange()
    plot_widget.setMouseEnabled(x=True, y=True)
    plot_widget.showGrid(x=True, y=True)

    colors = ["r", "g", "b", "y"]
    for i, column in enumerate(data.columns):
        y = pd.to_numeric(data[column], errors="coerce").fillna(0.0).astype(float)
        x = np.arange(len(y), dtype=float)
        plot_widget.plot(
            x,
            y.values,
            pen=pg.mkPen(color=colors[i % len(colors)], width=1.5),
            name=column,
        )
