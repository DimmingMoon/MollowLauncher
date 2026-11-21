import hashlib
import random

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget, QFrame

from ...config import NAME_RE
from ..avatar import face
from .. import icons
from ..theme import repolish, tm
from ..widgets import Btn, ElidedLabel, card_frame, clear_layout, label, scrolled

AV = 56


class AccountRow(QFrame):
    def __init__(self, acc, active, page):
        super().__init__()
        self.acc, self.page = acc, page
        self.setProperty("card", True)
        self.setProperty("active", active)
        self.setProperty("clickable", not active)
        self.setCursor(Qt.CursorShape.PointingHandCursor if not active else Qt.CursorShape.ArrowCursor)
        av = QWidget()
        av.setFixedSize(AV, AV)
        pic = QLabelPix(face(acc["name"]), av)
        name = ElidedLabel(acc["name"])
        name.setProperty("role", "h3")
        uid = label(acc["uuid"], "muted")
        col = QVBoxLayout()
        col.setSpacing(3)
        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(name)
        if active:
            chip = label("Активный", "chip")
            head.addWidget(chip)
        head.addStretch()
        col.addLayout(head)
        col.addWidget(uid)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(16)
        lay.addWidget(av)
        lay.addLayout(col, 1)
        if not active:
            use = Btn("Выбрать", "check")
            use.clicked.connect(lambda: page.use(acc["name"]))
            lay.addWidget(use)
        cp = Btn("", "copy", "ghost")
        cp.setToolTip("Скопировать UUID")
        cp.clicked.connect(lambda: (QApplication.clipboard().setText(acc["uuid"]), page.ctl.toast("UUID скопирован")))
        rm = Btn("", "trash", "ghost")
        rm.setToolTip("Удалить аккаунт")
        rm.clicked.connect(lambda: page.remove(acc["name"]))
        lay.addWidget(cp)
        lay.addWidget(rm)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and not self.property("active"):
            self.page.use(self.acc["name"])


def QLabelPix(pm, parent):
    from PyQt6.QtWidgets import QLabel
    lb = QLabel(parent)
    lb.setPixmap(pm)
    lb.setFixedSize(AV, AV)
    return lb


class AccountsPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.nick = QLineEdit()
        self.nick.setPlaceholderText("Ник игрока, например Steve_01")
        self.nick.setMaxLength(16)
        self.nick.returnPressed.connect(self.add)
        self.err = label("", "error")
        add = Btn("Добавить", "plus", "primary")
        add.clicked.connect(self.add)

        f, l = card_frame()
        l.addWidget(label("Новый аккаунт", "h2"))
        l.addWidget(label("Офлайн-вход без лицензии: достаточно ника (3–16 символов: латиница, цифры, _). "
                          "UUID считается так же, как это делает сам Minecraft, поэтому миры и инвентарь "
                          "привязаны к нику.", "muted", wrap=True))
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.nick, 1)
        row.addWidget(add)
        l.addLayout(row)
        l.addWidget(self.err)

        self.host = QWidget()
        self.rows = QVBoxLayout(self.host)
        self.rows.setContentsMargins(0, 0, 8, 0)
        self.rows.setSpacing(10)
        self.empty = label("Аккаунтов пока нет — добавьте первый ник выше.", "muted")
        self.count = label("", "chip")

        head = QHBoxLayout()
        head.addWidget(label("Мои аккаунты", "h2"))
        head.addWidget(self.count)
        head.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 20, 24)
        root.setSpacing(14)
        root.addWidget(label("Аккаунты", "h1"))
        root.addWidget(f)
        root.addLayout(head)
        root.addWidget(scrolled(self.host), 1)

    def refresh(self):
        cfg = self.ctl.cfg
        clear_layout(self.rows, keep=(self.empty,))  # empty — постоянная метка, её нельзя удалять
        accs = cfg["accounts"]
        self.count.setText(str(len(accs)))
        if not accs:
            self.rows.addWidget(self.empty)
            self.empty.show()
        for a in accs:
            self.rows.addWidget(AccountRow(a, a["name"] == cfg["selected"], self))
        self.rows.addStretch()

    def add(self):
        name = self.nick.text().strip()
        if not NAME_RE.match(name):
            self.err.setText("Допустимы латиница, цифры и _ , длина 3–16 символов")
            return
        if any(a["name"].lower() == name.lower() for a in self.ctl.cfg["accounts"]):
            self.err.setText("Такой ник уже добавлен")
            return
        self.err.setText("")
        self.nick.clear()
        self.ctl.cfg.add_account(name)
        self.ctl.refresh_all()
        self.ctl.toast(f"Аккаунт {name} добавлен")

    def use(self, name):
        self.ctl.cfg["selected"] = name
        self.ctl.cfg.save()
        self.ctl.refresh_all()
        self.ctl.toast(f"Активный аккаунт: {name}")

    def remove(self, name):
        def do():
            self.ctl.cfg.remove_account(name)
            self.ctl.refresh_all()

        self.ctl.confirm("Удалить аккаунт?",
                         f"Ник «{name}» будет убран из лаунчера. Миры и сборки не удаляются.",
                         do, "Удалить", danger=True)
