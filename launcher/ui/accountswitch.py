from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMenu, QPushButton

from . import icons
from .avatar import face
from .theme import tm


class AccountSwitch(QPushButton):
    """Кнопка внизу боковой панели: текущий аккаунт и быстрый выбор другого."""

    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.setProperty("acc", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIconSize(QSize(28, 28))
        self.setFixedHeight(50)
        self.clicked.connect(self.show_menu)
        tm.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        acc = self.ctl.cfg.selected_account()
        if acc:
            self.setIcon(QIcon(face(acc["name"], 28)))
            self.setText("  " + acc["name"] + "   ▾")
        else:
            self.setIcon(icons.icon("user", tm.p.text2, 22))
            self.setText("  Нет аккаунта   ▾")

    def show_menu(self):
        cfg = self.ctl.cfg
        m = QMenu(self)
        m.setMinimumWidth(self.width())
        for a in cfg["accounts"]:
            act = m.addAction(QIcon(face(a["name"], 22)), a["name"])
            act.setCheckable(True)
            act.setChecked(a["name"] == cfg["selected"])
            act.triggered.connect(lambda _=False, n=a["name"]: self.choose(n))
        if cfg["accounts"]:
            m.addSeparator()
        m.addAction(icons.icon("user", tm.p.text, 18), "Управление аккаунтами…", lambda: self.ctl.go("accounts"))
        m.exec(self.mapToGlobal(QPoint(0, -m.sizeHint().height() - 6)))

    def choose(self, name):
        self.ctl.cfg["selected"] = name
        self.ctl.cfg.save()
        self.ctl.refresh_all()
        self.ctl.toast(f"Активный аккаунт: {name}")
