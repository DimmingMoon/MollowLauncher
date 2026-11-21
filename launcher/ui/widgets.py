"""Общие UI-виджеты дизайн-системы MollowLauncher."""
import time

from PyQt6.QtCore import QEvent, QPropertyAnimation, QRectF, QSize, Qt, QTimer, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QActionGroup, QColor, QFont, QIntValidator, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractButton, QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from .. import net
from . import icons
from .theme import mix, qc, repolish, tm


def fmt_bytes(n):
    return f"{n / 1048576:.1f} МБ" if n < 1 << 30 else f"{n / (1 << 30):.2f} ГБ"


def fmt_duration(sec):
    sec = int(sec)
    h, m = divmod(sec // 60, 60)
    if h:
        return f"{h} ч {m:02d} мин"
    if m:
        return f"{m} мин"
    return "< 1 мин" if sec > 0 else "0 мин"


def plural(n, forms):
    n10, n100 = n % 10, n % 100
    if n10 == 1 and n100 != 11:
        return f"{n} {forms[0]}"
    if 2 <= n10 <= 4 and not 12 <= n100 <= 14:
        return f"{n} {forms[1]}"
    return f"{n} {forms[2]}"


class ElidedLabel(QLabel):
    """Метка, которая обрезает длинный текст многоточием вместо переполнения.
    Желаемая ширина — по полному тексту (иначе в строке с растяжкой ник схлопывается в 0),
    а сжаться она может до нескольких пикселей."""

    _full = ""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full = text
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._apply()

    def setText(self, text):
        self._full = text
        self._apply()
        self.updateGeometry()

    def text(self):
        return self._full

    def sizeHint(self):
        base = super().sizeHint()
        return QSize(self.fontMetrics().horizontalAdvance(self._full) + 8, base.height())

    def minimumSizeHint(self):
        return QSize(12, super().minimumSizeHint().height())

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._apply()
            self.updateGeometry()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply()

    def _apply(self):
        w = self.width()
        shown = self._full if w <= 1 else self.fontMetrics().elidedText(
            self._full, Qt.TextElideMode.ElideRight, max(12, w))
        if shown != QLabel.text(self):
            QLabel.setText(self, shown)


class NumberEdit(QLineEdit):
    """Числовое поле в стиле остальных полей ввода (вместо QSpinBox)."""

    def __init__(self, value=0, lo=0, hi=65536, parent=None):
        super().__init__(parent)
        self.lo, self.hi = lo, hi
        self.setValidator(QIntValidator(0, 10_000_000, self))
        self.setMaximumWidth(160)
        self.setText(str(value))
        self.editingFinished.connect(lambda: self.setText(str(self.value())))

    def value(self):
        try:
            v = int(self.text() or 0)
        except ValueError:
            v = self.lo
        return min(max(v, self.lo), self.hi)

    def setValue(self, v):
        self.setText(str(v))


def label(text="", role=None, wrap=False):
    lb = QLabel(text)
    if role:
        lb.setProperty("role", role)
    lb.setWordWrap(wrap)
    return lb


class Btn(QPushButton):
    """Кнопка с иконкой, которая перекрашивается при смене темы."""

    def __init__(self, text="", icon_name=None, variant="secondary", size=18, parent=None):
        super().__init__(text, parent)
        self.icon_name, self.isize, self.variant = icon_name, size, variant
        self.setProperty("variant", variant)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIconSize(QSize(size, size))
        tm.changed.connect(self.refresh_icon)
        self.refresh_icon()

    def set_variant(self, v):
        self.variant = v
        self.setProperty("variant", v)
        repolish(self)
        self.refresh_icon()

    def refresh_icon(self):
        if self.icon_name:
            col = tm.p.on_primary if self.variant == "primary" else (
                "#ffffff" if self.variant == "danger_fill" else tm.p.text)
            self.setIcon(icons.icon(self.icon_name, col, self.isize))


class NavButton(QPushButton):
    def __init__(self, text, icon_name, parent=None):
        super().__init__("  " + text, parent)
        self.icon_name = icon_name
        self.setCheckable(True)
        self.setProperty("nav", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIconSize(QSize(20, 20))
        self.toggled.connect(lambda _: self.refresh_icon())
        tm.changed.connect(self.refresh_icon)
        self.refresh_icon()

    def refresh_icon(self):
        self.setIcon(icons.icon(self.icon_name, tm.p.primary if self.isChecked() else tm.p.text2, 20))


class MenuButton(QPushButton):
    """Кнопка с выпадающим списком взаимоисключающих вариантов."""
    changed = pyqtSignal(str)

    def __init__(self, title, options, current=None, icon_name=None, parent=None):
        super().__init__(parent)
        self.title, self.options = title, options
        self.icon_name = icon_name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIconSize(QSize(16, 16))
        self.menu = QMenu(self)
        self.group = QActionGroup(self)
        self.group.setExclusive(True)
        self.current = current or options[0][0]
        for key, text in options:
            a = self.menu.addAction(text)
            a.setCheckable(True)
            a.setData(key)
            a.setChecked(key == self.current)
            self.group.addAction(a)
        self.group.triggered.connect(lambda a: self.set_current(a.data(), True))
        self.setMenu(self.menu)
        tm.changed.connect(self.refresh)
        self.refresh()

    def set_current(self, key, emit=False):
        self.current = key
        for a in self.group.actions():
            a.setChecked(a.data() == key)
        self.refresh()
        if emit:
            self.changed.emit(key)

    def refresh(self):
        shown = dict(self.options).get(self.current, "")
        self.setText(f"{self.title}: {shown}  ▾" if self.title else f"{shown}  ▾")
        if self.icon_name:
            self.setIcon(icons.icon(self.icon_name, tm.p.text, 16))


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self._k = 1.0 if checked else 0.0
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(140)
        self.toggled.connect(self._go)

    def _get(self):
        return self._k

    def _set(self, v):
        self._k = v
        self.update()

    knob = pyqtProperty(float, _get, _set)

    def _go(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._k)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(mix(tm.p.border, tm.p.primary, self._k))
        p.drawRoundedRect(QRectF(0, 0, 44, 24), 12, 12)
        p.setBrush(QColor("white") if self._k > 0.5 else QColor(tm.p.text2))
        p.drawEllipse(QRectF(3 + self._k * 20, 3, 18, 18))


class StageList(QWidget):
    ROW = 34

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stages, self.cur, self.failed = [], -1, False
        tm.changed.connect(self.update)

    def set_stages(self, stages):
        self.stages, self.cur, self.failed = list(stages), -1, False
        self.setFixedHeight(max(1, len(stages)) * self.ROW)
        self.update()

    def set_current(self, idx, failed=False):
        self.cur, self.failed = idx, failed
        self.update()

    def finish_all(self):
        self.cur = len(self.stages)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = tm.p
        for i, name in enumerate(self.stages):
            cy = i * self.ROW + self.ROW / 2
            done, active = i < self.cur, i == self.cur
            if i < len(self.stages) - 1:
                p.setPen(QPen(QColor(pal.primary if done else pal.border), 2))
                p.drawLine(12, int(cy + 10), 12, int(cy + self.ROW - 10))
            r = QRectF(3, cy - 9, 18, 18)
            p.setPen(Qt.PenStyle.NoPen)
            if done:
                p.setBrush(QColor(pal.primary))
                p.drawEllipse(r)
                p.drawPixmap(int(r.x() + 3), int(r.y() + 3), icons.pix("check", pal.on_primary, 12))
            elif active:
                col = QColor(pal.danger if self.failed else pal.primary)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(col, 2.5))
                p.drawEllipse(r.adjusted(1, 1, -1, -1))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(col)
                p.drawEllipse(r.adjusted(5, 5, -5, -5))
            else:
                p.setBrush(QColor(pal.border))
                p.drawEllipse(r)
            p.setPen(QColor(pal.text if (done or active) else pal.text2))
            f = QFont(self.font())
            f.setBold(active)
            p.setFont(f)
            p.drawText(QRectF(34, cy - 12, self.width() - 34, 24),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)


NET_STAGES = ("Клиент Minecraft", "Библиотеки", "Ресурсы")


class ProgressBlock(QWidget):
    """Этапы + полоса прогресса + скорость. Показывает только реальные данные:
    байты — из net.STATS, файлы — из сигналов progress."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stages = StageList()
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 0)
        self.percent = label("", "h3")
        self.detail = label("", "muted")
        row = QHBoxLayout()
        row.addWidget(self.bar, 1)
        row.addWidget(self.percent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(self.stages)
        lay.addSpacing(6)
        lay.addLayout(row)
        lay.addWidget(self.detail)
        self.msg, self.files = "", (0, 0)
        self._last = (time.monotonic(), 0)
        self.speed = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(400)
        self.timer.timeout.connect(self.tick)

    def start(self, stages):
        self.stages.set_stages(stages)
        self.msg, self.files, self.speed = "", (0, 0), 0.0
        self._last = (time.monotonic(), net.STATS["bytes"])
        self.bar.setRange(0, 0)
        self.percent.setText("")
        self.detail.setText("")
        self.timer.start()

    def set_stage(self, name):
        self.msg, self.files = name, (0, 0)
        if name in self.stages.stages:
            self.stages.set_current(self.stages.stages.index(name))
        self.tick()

    def on_progress(self, msg, done, total):
        if msg != self.msg:
            self.set_stage(msg)
        self.files = (done, total)
        self.tick()

    def tick(self):
        now = time.monotonic()
        b = net.STATS["bytes"]
        dt = now - self._last[0]
        if dt >= 0.8:
            self.speed = max(0.0, (b - self._last[1]) / dt)
            self._last = (now, b)
        net_stage = self.msg in NET_STAGES or self.msg.startswith("Скачивание Java")
        st, sb = net.STATS["stage_total"], net.STATS["stage_bytes"]
        done, total = self.files
        parts = []
        if net_stage and st:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(min(sb, st) / st * 1000))
            self.percent.setText(f"{min(sb, st) / st * 100:.0f}%")
        elif total > 1:
            self.bar.setRange(0, total)
            self.bar.setValue(done)
            self.percent.setText(f"{done / total * 100:.0f}%")
        else:
            self.bar.setRange(0, 0)
            self.percent.setText("")
        if total > 1:
            parts.append(f"{done}/{total} файлов")
        if net_stage and sb:
            parts.append(f"{fmt_bytes(sb)} / {fmt_bytes(st)}" if st else fmt_bytes(sb))
            if self.speed > 0:
                parts.append(f"{self.speed / 1048576:.1f} МБ/с")
        self.detail.setText((self.msg + ": " if self.msg else "") + " · ".join(parts) if parts else self.msg)

    def finish(self, ok=True):
        self.timer.stop()
        if ok:
            self.stages.finish_all()
            self.bar.setRange(0, 1)
            self.bar.setValue(1)
            self.percent.setText("100%")

    def fail(self):
        self.timer.stop()
        self.stages.set_current(self.stages.cur, failed=True)
        self.bar.setRange(0, 1)
        self.bar.setValue(0)


class LogView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(10000)
        self.text.setMinimumHeight(180)
        cp = Btn("Копировать лог", "copy", size=16)
        cp.clicked.connect(lambda: QApplication.clipboard().setText(self.text.toPlainText()))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.text)
        row = QHBoxLayout()
        row.addWidget(cp)
        row.addStretch()
        lay.addLayout(row)

    def append(self, s):
        self.text.appendPlainText(s.rstrip("\n"))

    def clear(self):
        self.text.clear()


class SearchEdit(QLineEdit):
    def __init__(self, placeholder="Поиск…", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self._act = self.addAction(icons.icon("search", tm.p.text2, 18), QLineEdit.ActionPosition.LeadingPosition)
        tm.changed.connect(lambda: self._act.setIcon(icons.icon("search", tm.p.text2, 18)))


def clear_layout(layout, keep=()):
    """Убирает всё из layout. Виджеты прячутся и удаляются отложенно (deleteLater) — без setParent(None),
    который превращал живой виджет в отдельное окно. Виджеты из keep не удаляются, а только прячутся."""
    while layout.count():
        it = layout.takeAt(0)
        w = it.widget()
        if w is None:
            continue
        w.hide()
        if w not in keep:
            w.deleteLater()


def scrolled(widget):
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setWidget(widget)
    return sa


def card_frame(layout=None, margins=(20, 18, 20, 18), spacing=10):
    f = QFrame()
    f.setProperty("card", True)
    lay = layout or QVBoxLayout()
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    f.setLayout(lay)
    return f, lay
