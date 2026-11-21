import hashlib
import random

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPixmap


def face(name, size=56):
    """Пиксельное «лицо» игрока 8×8: цвета выбираются по нику (у каждого ника своё)."""
    rnd = random.Random(int(hashlib.md5(name.lower().encode()).hexdigest(), 16))
    skin = QColor(rnd.choice(["#F1C27D", "#E0AC86", "#C68642", "#8D5524", "#FFDBAC"]))
    hair = QColor(rnd.choice(["#3B2A1A", "#1E1E1E", "#6B4423", "#C9A227", "#8B2E16", "#4A4A8A"]))
    eye = QColor(rnd.choice(["#3A6EA5", "#2E7D32", "#4E342E", "#555555"]))
    img = QImage(8, 8, QImage.Format.Format_ARGB32)
    for y in range(8):
        for x in range(8):
            c = skin
            if y < 2 or (y == 2 and x in (0, 7)):
                c = hair
            if y == 4 and x in (1, 6):
                c = QColor("#FFFFFF")
            if y == 4 and x in (2, 5):
                c = eye
            if y == 6 and x in (3, 4):
                c = skin.darker(150)
            img.setPixelColor(x, y, c)
    pm = QPixmap.fromImage(img).scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.FastTransformation)
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), size * 0.25, size * 0.25)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pm)
    p.end()
    return out
