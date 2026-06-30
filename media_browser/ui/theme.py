"""Cosmic-glow / Linear-style dark theme for the media browser window.

Qt Style Sheets can't do real box shadows, so "glow" is approximated with
gradient fills, accent borders and translucent panels over a deep-space radial
background.
"""
from __future__ import annotations

SCIFI_STYLESHEET = """
QMainWindow {
    background: #060610;
}
/* ID selector beats the generic `QWidget { background: transparent }` rule below,
   so the deep-space gradient actually paints behind the transparent panels. */
#Root {
    background: qradialgradient(cx:0.22, cy:0.0, radius:1.45, fx:0.22, fy:0.0,
        stop:0 #1b1640, stop:0.42 #110f24, stop:1 #060610);
}
QWidget {
    background: transparent;
    color: #e6e8f4;
    font-size: 13px;
}
QLabel {
    font-weight: 600;
    color: #c5c9e6;
    background: transparent;
}

QLineEdit, QComboBox, QTextEdit, QListWidget {
    background: rgba(255, 255, 255, 0.035);
    color: #e6e8f4;
    border: 1px solid #2b2b44;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #6d5dfc;
    selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #7c5cff;
    background: rgba(124, 92, 255, 0.08);
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #14122a;
    color: #e6e8f4;
    border: 1px solid #2b2b44;
    border-radius: 8px;
    selection-background-color: #6d5dfc;
    outline: none;
}

#PreviewFrame {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0d0b1c, stop:1 #08070f);
    border: 1px solid #2c2650;
    border-radius: 12px;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c4dff, stop:1 #2d7bff);
    border: 1px solid rgba(150, 130, 255, 0.55);
    border-radius: 10px;
    padding: 9px 16px;
    color: #ffffff;
    font-weight: 700;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9266ff, stop:1 #3f8bff);
    border: 1px solid #b39bff;
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6a3ce0, stop:1 #2569e0);
}
QPushButton:disabled {
    background: rgba(255, 255, 255, 0.05);
    color: #6b6f88;
    border: 1px solid transparent;
}

QListWidget {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid #1f1f33;
    border-radius: 12px;
    padding: 6px;
}
QListWidget::item {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid #24243c;
    border-radius: 10px;
    padding: 6px;
    margin: 6px;
    color: #b7bbd8;
}
QListWidget::item:hover {
    border: 1px solid #4a3f86;
    background: rgba(124, 92, 255, 0.10);
}
QListWidget::item:selected {
    border: 1px solid #9a7bff;
    background: rgba(124, 92, 255, 0.22);
    color: #ffffff;
}

QProgressBar {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid #2b2b44;
    border-radius: 8px;
    text-align: center;
    color: #e6e8f4;
    min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c4dff, stop:0.5 #4d7bff, stop:1 #22d3ee);
    border-radius: 7px;
}
#BusyBar, #LoadingBar {
    background: rgba(255, 255, 255, 0.04);
    border: none;
    border-radius: 2px;
}
#BusyBar::chunk, #LoadingBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c4dff, stop:0.5 #22d3ee, stop:1 #7c4dff);
    border-radius: 2px;
}

QStatusBar {
    background: transparent;
    color: #8b8fb0;
    border-top: 1px solid #1b1b2c;
}
QStatusBar::item { border: none; }

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #2f2f4a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #5b4fd6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #2f2f4a;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #5b4fd6; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QToolTip {
    background: #14122a;
    color: #e6e8f4;
    border: 1px solid #3a3360;
    border-radius: 6px;
    padding: 6px;
}
QDialog, QMessageBox { background: #0e0c1c; }
QCheckBox { background: transparent; color: #c5c9e6; }
"""
