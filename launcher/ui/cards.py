"""Карточка игровой сборки и сетка карточек."""
from PyQt6.QtCore import QPropertyAnimation, QRectF, QSize, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu, QToolButton, QVBoxLayout, QWidget,
)

from .. import covers
from . import icons
from .theme import mix, tm
from .widgets import Btn, ElidedLabel, fmt_duration, label, plural

CARD_W, CARD_H, COVER_H = 252, 320, 150


class InstanceCard(QFrame):
    action = pyqtSignal(str, str)  # inst_id, action

    def __init__(self, inst, selected=False, running=False, parent=None):
        super().__init__(parent)
        self.inst, self.selected, self.running = inst, selected, running
        self._hover = 0.0
        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menu)
        self._anim = QPropertyAnimation(self, b"hover", self)
        self._anim.setDuration(140)

        d = inst.data
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, COVER_H + 14, 16, 16)
        lay.setSpacing(6)
        self.title = ElidedLabel(inst.name)
        self.title.setProperty("role", "h3")
        self.title.setToolTip(inst.name)
        lay.addWidget(self.title)
        self.info_icons = []
        r1 = QHBoxLayout()
        r1.setSpacing(0)
        r1.addLayout(self._pair("tag", d["mc_version"]))
        r1.addSpacing(14)
        r1.addLayout(self._pair("layers", inst.loader_label))
        r1.addStretch()
        r2 = QHBoxLayout()
        r2.setSpacing(0)
        r2.addLayout(self._pair("mods", plural(inst.mod_count, ("мод", "мода", "модов"))))
        r2.addSpacing(14)
        r2.addLayout(self._pair("clock", fmt_duration(d.get("play_time", 0))))
        r2.addStretch()
        lay.addLayout(r1)
        lay.addLayout(r2)
        lay.addStretch()
        row = QHBoxLayout()
        row.setSpacing(8)
        self.gear = QToolButton()
        self.gear.setToolTip("Настройки сборки")
        self.gear.setFixedSize(40, 40)
        self.gear.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.gear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gear.clicked.connect(lambda: self.action.emit(inst.id, "settings"))
        if running:
            self.play = Btn("Остановить игру", "stop", "danger_fill", 16)
            self.play.clicked.connect(lambda: self.action.emit(inst.id, "stop"))
        else:
            self.play = Btn("Играть", "play", "primary" if selected else "secondary", 16)
            self.play.clicked.connect(lambda: self.action.emit(inst.id, "play"))
        self.play.setFixedHeight(40)
        row.addWidget(self.gear)
        row.addWidget(self.play, 1)
        lay.addLayout(row)

        self.star = QToolButton(self)
        self.star.setFixedSize(34, 34)
        self.star.move(CARD_W - 48, 14)
        self.star.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.star.setCursor(Qt.CursorShape.PointingHandCursor)
        self.star.clicked.connect(lambda: self.action.emit(inst.id, "favorite"))
        tm.changed.connect(self.refresh_icons)
        self.refresh_icons()

    def _pair(self, icon_name, text):
        lay = QHBoxLayout()
        lay.setSpacing(6)
        pic = QLabel()
        pic.setFixedSize(16, 16)
        self.info_icons.append((pic, icon_name))
        t = label(text, "muted")
        lay.addWidget(pic)
        lay.addWidget(t)
        return lay

    def refresh_icons(self):
        p = tm.p
        for pic, ic in self.info_icons:
            pic.setPixmap(icons.pix(ic, p.text2, 16))
        self.gear.setIcon(icons.icon("settings", p.text, 20))
        fav = self.inst.data.get("favorite", False)
        self.star.setIcon(icons.icon("star", p.primary if fav else "#ffffff", 18, filled=fav))
        self.star.setToolTip("Убрать из избранного" if fav else "В избранное")
        self.star.setStyleSheet("QToolButton{background:rgba(0,0,0,110);border-radius:17px;}"
                                "QToolButton:hover{background:rgba(0,0,0,170);}")

    def set_selected(self, v):
        self.selected = v
        if not self.running:
            self.play.set_variant("primary" if v else "secondary")
        self.update()

    def get_hover(self):
        return self._hover

    def set_hover(self, v):
        self._hover = v
        self.update()

    hover = pyqtProperty(float, get_hover, set_hover)

    def enterEvent(self, e):
        self._anim.stop()
        self._anim.setEndValue(1.0)
        self._anim.start()

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setEndValue(0.0)
        self._anim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.action.emit(self.inst.id, "select")

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.action.emit(self.inst.id, "logs" if self.running else "play")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = tm.p
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        path = QPainterPath()
        path.addRoundedRect(r, 16, 16)
        p.fillPath(path, QColor(pal.surface))
        p.save()
        p.setClipPath(path)
        p.drawPixmap(0, 0, covers.pixmap(self.inst, self.width(), COVER_H))
        p.restore()
        if self.running:  # плашка «Запущена»
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 165))
            p.drawRoundedRect(QRectF(14, 14, 98, 28), 14, 14)
            p.setBrush(QColor(pal.primary))
            p.drawEllipse(QRectF(24, 24, 8, 8))
            f = QFont(self.font())
            f.setBold(True)
            f.setPointSize(9)
            p.setFont(f)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(38, 14, 72, 28), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Запущена")
        if self.selected:
            p.setPen(QPen(QColor(pal.primary), 2.5))
        else:
            p.setPen(QPen(mix(pal.border, pal.primary, self._hover), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, 16, 16)

    def menu(self, pos):
        fav = self.inst.data.get("favorite", False)
        m = QMenu(self)
        first = (("logs", "Окно запуска и логи"), ("stop", "Остановить игру")) if self.running \
            else (("play", "Играть"),)
        entries = list(first) + [("settings", "Настройки и моды"), ("folder", "Открыть папку"), None,
                                 ("cover", "Сменить обложку…"), ("cover_reset", "Стандартная обложка"),
                                 ("favorite", "Убрать из избранного" if fav else "В избранное"), None,
                                 ("clone", "Копировать сборку"), ("delete", "Удалить сборку")]
        for e in entries:
            if e is None:
                m.addSeparator()
            else:
                m.addAction(e[1], lambda _=False, k=e[0]: self.action.emit(self.inst.id, k))
        m.exec(self.mapToGlobal(pos))


class CardGrid(QWidget):
    """Адаптивная сетка карточек (число колонок зависит от ширины)."""
    action = pyqtSignal(str, str)

    def __init__(self, empty_text="Здесь пока пусто", parent=None):
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(16)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.empty = label(empty_text, "muted", wrap=True)
        self.cards, self.selected = [], None

    def set_instances(self, insts, selected=None, running=()):
        self.selected = selected
        self.relayout_clear()
        self.cards = []
        for inst in insts:
            c = InstanceCard(inst, inst.id == selected, inst.id in running)
            c.action.connect(self._on_action)
            self.cards.append(c)
        self.relayout()

    def relayout_clear(self):
        for c in self.cards:
            c.hide()
            c.deleteLater()
        while self.grid.count():
            self.grid.takeAt(0)

    def set_selected(self, inst_id):
        self.selected = inst_id
        for c in self.cards:
            c.set_selected(c.inst.id == inst_id)

    def _on_action(self, inst_id, act):
        if act == "select":
            self.set_selected(inst_id)
        self.action.emit(inst_id, act)

    def relayout(self):
        while self.grid.count():
            self.grid.takeAt(0)
        if not self.cards:
            self.grid.addWidget(self.empty, 0, 0)
            self.empty.show()
            return
        self.empty.hide()
        cols = max(1, (self.width() + 16) // (CARD_W + 16))
        for i, c in enumerate(self.cards):
            self.grid.addWidget(c, i // cols, i % cols)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.relayout()
