"""Фон лаунчера: картинка за страницами (страницы прозрачные, карточки — нет)."""
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget

from .. import covers, paths
from .theme import tm


class Backdrop(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self._src, self._key = None, None
        tm.changed.connect(self.update)

    def reload(self):
        self._key = None
        self.update()

    def _source(self):
        mode = self.ctl.cfg["background"]
        f = paths.DATA / "background.png"
        stamp = f.stat().st_mtime_ns if mode == "custom" and f.exists() else 0
        key = (mode, stamp)
        if key != self._key:
            self._key, self._src = key, None
            if mode == "custom" and stamp:
                pm = QPixmap(str(f))
                self._src = None if pm.isNull() else pm
            elif mode.startswith("scene:"):
                try:
                    self._src = covers.preset_source(int(mode.split(":", 1)[1]))
                except ValueError:
                    self._src = None
        return self._src

    def paintEvent(self, _):
        src = self._source()
        if src is None:  # «Нет» — виден обычный цвет окна
            return
        p = QPainter(self)
        w, h = self.width(), self.height()
        k = max(w / src.width(), h / src.height())  # «cover»: заполнить, лишнее обрезать
        vw, vh = w / k, h / k
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self.ctl.cfg["background"] == "custom")
        p.drawPixmap(QRectF(0, 0, w, h), src, QRectF((src.width() - vw) / 2, (src.height() - vh) / 2, vw, vh))
        c = QColor(tm.p.bg)
        c.setAlpha(int(self.ctl.cfg["bg_dim"] * 2.55))
        p.fillRect(self.rect(), c)
