"""Собственная шапка окна (вместо системной белой) и «ручки» для изменения размера."""
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QWidget

from .. import paths
from . import icons
from .theme import tm


class WinButton(QToolButton):
    def __init__(self, kind, icon_name):
        super().__init__()
        self.kind, self.name = kind, icon_name
        self.setProperty("wbtn", kind)
        self.setFixedSize(48, 40)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIconSize(QSize(16, 16))
        tm.changed.connect(self.refresh_icon)
        self.refresh_icon()

    def set_icon_name(self, name):
        self.name = name
        self.refresh_icon()

    def refresh_icon(self):
        self.setIcon(icons.icon(self.name, tm.p.text, 16))

    def enterEvent(self, e):
        if self.kind == "close":
            self.setIcon(icons.icon(self.name, "#ffffff", 16))

    def leaveEvent(self, e):
        self.refresh_icon()


class TitleBar(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(40)
        ic = QLabel()
        ic.setPixmap(QPixmap(str(paths.resource("assets/icon.png"))).scaled(
            22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        title = QLabel(paths.APP_NAME)
        title.setProperty("role", "muted")
        self.b_min = WinButton("min", "minimize")
        self.b_max = WinButton("max", "maximize")
        self.b_close = WinButton("close", "close")
        self.b_min.clicked.connect(win.showMinimized)
        self.b_max.clicked.connect(self.toggle)
        self.b_close.clicked.connect(win.close)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(ic)
        lay.addWidget(title)
        lay.addStretch()
        for b in (self.b_min, self.b_max, self.b_close):
            lay.addWidget(b)

    def toggle(self):
        if self.win.isMaximized():
            self.win.showNormal()
        else:
            self.win.showMaximized()

    def sync(self):
        self.b_max.set_icon_name("restore" if self.win.isMaximized() else "maximize")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            h = self.window().windowHandle()
            if h:
                h.startSystemMove()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.toggle()


class EdgeGrip(QWidget):
    """Невидимая полоска у края окна: тянешь — меняется размер."""

    def __init__(self, parent, edges, cursor):
        super().__init__(parent)
        self.edges = edges
        self.setCursor(cursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            h = self.window().windowHandle()
            if h:
                h.startSystemResize(self.edges)
