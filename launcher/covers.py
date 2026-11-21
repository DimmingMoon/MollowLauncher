"""Data management: обложки сборок. Пользовательская обложка хранится в папке
самой сборки (cover.png), стандартная рисуется программно."""
import hashlib
import random

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap

COVER_W, COVER_H = 960, 540
_cache = {}

SCENES = [  # (верх, середина, низ, солнце, тёмная?)
    ("#2b1b4a", "#d9583b", "#ffb347", "#fff2b0", True),
    ("#120b24", "#3a1b6b", "#7c3aed", "#e9ddff", True),
    ("#f4a8c8", "#f8cfe0", "#bfe3ff", "#ffffff", False),
    ("#4aa8ff", "#8fd0ff", "#d6f0ff", "#fffbe0", False),
    ("#071a14", "#14543a", "#38b583", "#d7ffe9", True),
    ("#0e1b33", "#1f4f8f", "#5fa8ff", "#f2f7ff", True),
]


def set_cover(inst, src_path):
    img = QImage(str(src_path))
    if img.isNull():
        raise ValueError("Не удалось открыть изображение")
    img = img.scaled(COVER_W, COVER_H, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                     Qt.TransformationMode.SmoothTransformation)
    x, y = (img.width() - COVER_W) // 2, (img.height() - COVER_H) // 2
    img = img.copy(x, y, COVER_W, COVER_H)
    if not img.save(str(inst.cover_path), "PNG"):
        raise IOError("Не удалось сохранить обложку")
    _cache.clear()


def reset_cover(inst):
    inst.cover_path.unlink(missing_ok=True)
    _cache.clear()


def has_cover(inst):
    return inst.cover_path.exists()


def _generated(name, w, h):
    rnd = random.Random(int(hashlib.md5(name.encode()).hexdigest(), 16))
    top, mid, bot, sun, dark = rnd.choice(SCENES)
    pm = QPixmap(w, h)
    p = QPainter(pm)
    g = QLinearGradient(0, 0, 0, h)
    g.setColorAt(0, QColor(top))
    g.setColorAt(0.55, QColor(mid))
    g.setColorAt(1, QColor(bot))
    p.fillRect(0, 0, w, h, g)
    u = max(4, h // 28)  # размер «пикселя»
    if dark:
        for _ in range(26):
            c = QColor("white")
            c.setAlpha(rnd.randint(60, 200))
            p.fillRect(rnd.randrange(0, w // u) * u, rnd.randrange(0, h // 2 // u) * u, u // 2 + 1, u // 2 + 1, c)
    s = u * 4
    p.fillRect(int(w * rnd.uniform(0.15, 0.8)), int(h * rnd.uniform(0.12, 0.3)), s, s, QColor(sun))
    for layer, (col, base, amp) in enumerate((("#000000", 0.62, 0.10), ("#000000", 0.76, 0.12))):
        c = QColor(col)
        c.setAlpha(90 if layer == 0 else 190)
        hgt = base * h
        for x in range(0, w + u, u):
            hgt += rnd.choice((-u, 0, 0, u))
            hgt = min(max(hgt, (base - amp) * h), (base + amp) * h)
            top_y = int(hgt // u * u)
            p.fillRect(x, top_y, u, h - top_y, c)
            if layer == 1 and rnd.random() < 0.07:  # «деревья»
                p.fillRect(x, top_y - u * 3, u, u * 3, c)
                p.fillRect(x - u, top_y - u * 4, u * 3, u * 2, c)
    p.end()
    return pm


def pixmap(inst, w, h):
    """Обложка (пользовательская или стандартная), обрезанная под w×h."""
    stamp = inst.cover_path.stat().st_mtime_ns if has_cover(inst) else 0
    key = (inst.id, inst.name, stamp, w, h)
    if key in _cache:
        return _cache[key]
    if stamp:
        src = QPixmap(str(inst.cover_path))
    else:
        src = _generated(inst.name, COVER_W, COVER_H)
    if src.isNull():
        src = _generated(inst.name, COVER_W, COVER_H)
    out = src.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                     Qt.TransformationMode.SmoothTransformation)
    out = out.copy((out.width() - w) // 2, (out.height() - h) // 2, w, h)
    if len(_cache) > 64:
        _cache.clear()
    _cache[key] = out
    return out
