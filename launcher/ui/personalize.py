"""Персонализация: цвет кнопок (палитра + свой цвет), тема лаунчера, фон."""
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QImage, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLineEdit, QSlider, QToolButton, QVBoxLayout,
    QWidget,
)

from .. import covers, paths
from .theme import PALETTES, tm, valid_hex
from .widgets import Btn, label

# None — «цвет по умолчанию» (цвет выбранной темы)
SWATCHES = [None, "#A3D930", "#20C9AC", "#26B5E8", "#4A8CFF", "#6D6DFF", "#9B6BFF", "#FF69B4", "#FF6B5E",
            "#FF9A3D", "#F7C93E", "#2DB56F", "#5DDDB0", "#6DC8FF", "#3D6FE0", "#B49CFF", "#E8457E", "#FF8A6B",
            "#FFB020", "#D9B26F", "#C3CBD3"]
COLS = 11


def _dot(color):
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, 16, 16)
    p.end()
    return QIcon(pm)


class SVSquare(QWidget):
    """Квадрат насыщенность/яркость выбранного оттенка."""
    moved = pyqtSignal(float, float, bool)  # s, v, закончили ли тянуть

    def __init__(self):
        super().__init__()
        self.h, self.s, self.v = 0.4, 0.7, 0.8
        self.setFixedSize(220, 140)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, _):
        p = QPainter(self)
        r = QRectF(self.rect())
        g1 = QLinearGradient(r.left(), 0, r.right(), 0)
        g1.setColorAt(0, QColor("white"))
        g1.setColorAt(1, QColor.fromHsvF(min(self.h, 0.999), 1, 1))
        p.fillRect(r, g1)
        g2 = QLinearGradient(0, r.top(), 0, r.bottom())
        g2.setColorAt(0, QColor(0, 0, 0, 0))
        g2.setColorAt(1, QColor("black"))
        p.fillRect(r, g2)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(self.s * r.width(), (1 - self.v) * r.height()), 6, 6)

    def _set(self, e):
        pt = e.position()
        self.s = min(max(pt.x() / self.width(), 0.0), 1.0)
        self.v = 1.0 - min(max(pt.y() / self.height(), 0.0), 1.0)
        self.update()

    def mousePressEvent(self, e):
        self._set(e)
        self.moved.emit(self.s, self.v, False)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._set(e)
            self.moved.emit(self.s, self.v, False)

    def mouseReleaseEvent(self, e):
        self.moved.emit(self.s, self.v, True)


class HueBar(QWidget):
    moved = pyqtSignal(float, bool)

    def __init__(self):
        super().__init__()
        self.h = 0.4
        self.setFixedSize(220, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), 0)
        for i in range(7):
            g.setColorAt(i / 6, QColor.fromHsvF(min(i / 6, 0.999), 1, 1))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(QRectF(self.rect()), 8, 8)
        p.setBrush(QColor("white"))
        p.setPen(QPen(QColor(0, 0, 0, 120), 1))
        p.drawEllipse(QPointF(8 + self.h * (self.width() - 16), 8), 7, 7)

    def _set(self, e):
        self.h = min(max((e.position().x() - 8) / (self.width() - 16), 0.0), 1.0)
        self.update()

    def mousePressEvent(self, e):
        self._set(e)
        self.moved.emit(self.h, False)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._set(e)
            self.moved.emit(self.h, False)

    def mouseReleaseEvent(self, e):
        self.moved.emit(self.h, True)


class ColorPicker(QFrame):
    """Выбор цвета прямо в окне (не отдельным диалогом). Применяется, когда отпустили мышь или нажали Enter."""
    committed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.sv, self.hue = SVSquare(), HueBar()
        self.sv.moved.connect(self._on_sv)
        self.hue.moved.connect(self._on_hue)
        self.swatch = QFrame()
        self.swatch.setFixedSize(34, 34)
        self.hex = QLineEdit()
        self.hex.setMaxLength(7)
        self.hex.setFixedWidth(120)
        self.hex.editingFinished.connect(self._typed)
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.swatch)
        row.addWidget(self.hex)
        row.addStretch()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(self.sv)
        lay.addWidget(self.hue)
        lay.addLayout(row)
        self._sync()

    def _color(self):
        return QColor.fromHsvF(min(self.sv.h, 0.999), self.sv.s, self.sv.v)

    def _sync(self):
        c = self._color()
        self.hex.setText(c.name().upper())
        self.swatch.setStyleSheet(f"background:{c.name()};border-radius:8px;border:1px solid {tm.p.border};")

    def set_color(self, hex_color):
        c = QColor(hex_color)
        if not c.isValid():
            return
        h = c.hsvHueF()
        if h >= 0:  # у серых оттенок не определён — оставляем прежний
            self.sv.h = self.hue.h = h
        self.sv.s, self.sv.v = c.hsvSaturationF(), c.valueF()
        self.sv.update()
        self.hue.update()
        self._sync()

    def _on_sv(self, s, v, final):
        self._sync()
        if final:
            self.committed.emit(self._color().name())

    def _on_hue(self, h, final):
        self.sv.h = h
        self.sv.update()
        self._sync()
        if final:
            self.committed.emit(self._color().name())

    def _typed(self):
        t = self.hex.text().strip()
        t = t if t.startswith("#") else "#" + t
        if valid_hex(t):
            self.set_color(t)
            self.committed.emit(t.lower())
        else:
            self._sync()


class Personalize(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        cfg = ctl.cfg
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(label("Персонализация", "h2"))

        # --- цвет кнопок
        root.addWidget(label("Цвет кнопок", "muted"))
        grid = QGridLayout()
        grid.setSpacing(8)
        self.swatches = []
        for i, c in enumerate(SWATCHES):
            b = QToolButton()
            b.setCheckable(True)
            b.setFixedSize(38, 38)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setToolTip("По умолчанию (цвет темы)" if c is None else c.upper())
            b.clicked.connect(lambda _=False, col=c: self.set_accent(col or ""))
            self.swatches.append((b, c))
            grid.addWidget(b, i // COLS, i % COLS)
        self.plus = Btn("+", variant="ghost")
        self.plus.setFixedSize(38, 38)
        self.plus.setToolTip("Свой цвет")
        self.plus.clicked.connect(self.toggle_picker)
        grid.addWidget(self.plus, len(SWATCHES) // COLS, len(SWATCHES) % COLS)
        grid.setColumnStretch(COLS, 1)
        root.addLayout(grid)
        self.picker = ColorPicker()
        self.picker.hide()
        self.picker.committed.connect(self.set_accent)
        root.addWidget(self.picker, 0, Qt.AlignmentFlag.AlignLeft)

        # --- тема
        root.addSpacing(6)
        root.addWidget(label("Тема лаунчера", "muted"))
        trow = QHBoxLayout()
        self.tgroup = QButtonGroup(self)
        self.tgroup.setExclusive(True)
        self.theme_btns = {}
        for pid, pal in PALETTES.items():
            b = Btn(pal.label)
            b.setCheckable(True)
            b.setProperty("seg", True)
            b.setIcon(_dot(pal.primary))
            b.setChecked(pid == tm.base.id)
            b.clicked.connect(lambda _=False, k=pid: tm.set(k))
            self.tgroup.addButton(b)
            self.theme_btns[pid] = b
            trow.addWidget(b)
        trow.addStretch()
        root.addLayout(trow)

        # --- фон
        root.addSpacing(6)
        root.addWidget(label("Фон", "muted"))
        brow = QHBoxLayout()
        brow.setSpacing(8)
        self.bgroup = QButtonGroup(self)
        self.bgroup.setExclusive(True)
        self.bg_btns = {}

        def thumb(key, w=138, h=82):
            b = QToolButton()
            b.setProperty("thumb", True)
            b.setCheckable(True)
            b.setFixedSize(w, h)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.bgroup.addButton(b)
            self.bg_btns[key] = b
            brow.addWidget(b)
            return b

        b = thumb("none")
        b.setText("Нет")
        b.clicked.connect(lambda _=False: self.set_bg("none"))
        for i, (nm, _) in enumerate(covers.PRESETS):
            b = thumb(f"scene:{i}")
            b.setIcon(QIcon(covers.preset_pixmap(i, 128, 72)))
            b.setIconSize(QSize(128, 72))
            b.setToolTip(nm)
            b.clicked.connect(lambda _=False, k=f"scene:{i}": self.set_bg(k))
        b = thumb("custom")
        b.setText("Свой…")
        b.setToolTip("Выбрать своё изображение")
        b.clicked.connect(lambda _=False: self.pick_custom())
        brow.addStretch()
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.addLayout(brow)
        # картинки в ряд не помещаются на узком окне — разрешаем прокрутку по горизонтали
        from PyQt6.QtWidgets import QScrollArea
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.setFixedHeight(104)
        sa.setWidget(wrap)
        root.addWidget(sa)
        drow = QHBoxLayout()
        drow.addWidget(label("Затемнение фона", "muted"))
        self.dim = QSlider(Qt.Orientation.Horizontal)
        self.dim.setRange(20, 95)
        self.dim.setValue(int(cfg["bg_dim"]))
        self.dim.setFixedWidth(260)
        self.dim.valueChanged.connect(self.on_dim)
        self.dim.sliderReleased.connect(cfg.save)
        drow.addWidget(self.dim)
        drow.addStretch()
        root.addLayout(drow)

        tm.changed.connect(self.refresh)
        self.refresh()

    # ---------- состояние
    def refresh(self):
        cfg = self.ctl.cfg
        p = tm.p
        cur = (cfg["accent"] or "").lower()
        for b, c in self.swatches:
            col = tm.base.primary if c is None else c
            b.setStyleSheet(
                f"QToolButton{{background:{col};border:2px solid transparent;border-radius:10px;}}"
                f"QToolButton:hover{{border:2px solid {p.text2};}}"
                f"QToolButton:checked{{border:2px solid {p.text};}}")
            b.setChecked((c or "").lower() == cur)
        self.theme_btns[tm.base.id].setChecked(True)
        key = cfg["background"]
        (self.bg_btns.get(key) or self.bg_btns["none"]).setChecked(True)
        f = paths.DATA / "background.png"
        if f.exists():
            pm = QPixmap(str(f))
            if not pm.isNull():
                self.bg_btns["custom"].setIcon(QIcon(pm.scaled(
                    128, 72, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)))
                self.bg_btns["custom"].setIconSize(QSize(128, 72))
                self.bg_btns["custom"].setText("")

    # ---------- действия
    def set_accent(self, hex_color):
        tm.set_accent(hex_color)  # сам вызовет refresh через tm.changed
        if hex_color:
            self.picker.set_color(hex_color)

    def toggle_picker(self):
        show = not self.picker.isVisible()
        if show:
            self.picker.set_color(tm.p.primary)
        self.picker.setVisible(show)

    def set_bg(self, key):
        self.ctl.cfg["background"] = key
        self.ctl.cfg.save()
        self.ctl.backdrop.reload()

    def pick_custom(self):
        f, _ = QFileDialog.getOpenFileName(self, "Выберите изображение для фона", "",
                                           "Изображения (*.png *.jpg *.jpeg *.webp *.bmp)")
        if f:
            img = QImage(f)
            if img.isNull():
                self.ctl.toast("Не удалось открыть изображение", "error")
            else:
                if img.width() > 1920 or img.height() > 1080:  # больше экрана не нужно — экономим диск и память
                    img = img.scaled(1920, 1080, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                if img.save(str(paths.DATA / "background.png"), "PNG"):
                    self.set_bg("custom")
                else:
                    self.ctl.toast("Не удалось сохранить фон", "error")
        self.refresh()

    def on_dim(self, v):
        self.ctl.cfg["bg_dim"] = int(v)
        self.ctl.backdrop.update()
