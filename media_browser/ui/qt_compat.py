from __future__ import annotations


try:
    from PySide6.QtCore import Qt, QThread, Signal, QSize, QRect, QUrl
    from PySide6.QtGui import (
        QAction,
        QBrush,
        QColor,
        QDesktopServices,
        QFont,
        QIcon,
        QPainter,
        QPen,
        QPixmap,
    )
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSlider,
        QSplitter,
        QStatusBar,
        QTextEdit,
        QToolBar,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PySide2.QtCore import Qt, QThread, Signal, QSize, QRect, QUrl
    from PySide2.QtGui import (
        QBrush,
        QColor,
        QDesktopServices,
        QFont,
        QIcon,
        QPainter,
        QPen,
        QPixmap,
    )
    QAudioOutput = None
    try:
        from PySide2.QtMultimedia import QMediaPlayer
        from PySide2.QtMultimediaWidgets import QVideoWidget
    except ImportError:
        QMediaPlayer = None
        QVideoWidget = None
    from PySide2.QtWidgets import (
        QAction,
        QApplication,
        QAbstractItemView,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSlider,
        QSplitter,
        QStatusBar,
        QTextEdit,
        QToolBar,
        QVBoxLayout,
        QWidget,
    )


__all__ = [
    "QAction",
    "QApplication",
    "QAbstractItemView",
    "QAudioOutput",
    "QBrush",
    "QCheckBox",
    "QColor",
    "QComboBox",
    "QDesktopServices",
    "QDialog",
    "QDialogButtonBox",
    "QFont",
    "QFrame",
    "QGridLayout",
    "QHBoxLayout",
    "QIcon",
    "QLabel",
    "QLineEdit",
    "QListWidget",
    "QListWidgetItem",
    "QMainWindow",
    "QMessageBox",
    "QMediaPlayer",
    "QPainter",
    "QPen",
    "QPixmap",
    "QProgressBar",
    "QPushButton",
    "QRect",
    "QSlider",
    "QSize",
    "QSplitter",
    "QStatusBar",
    "QTextEdit",
    "QThread",
    "QToolBar",
    "Qt",
    "QUrl",
    "QVideoWidget",
    "QVBoxLayout",
    "QWidget",
    "Signal",
]
