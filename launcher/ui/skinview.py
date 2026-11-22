"""Предпросмотр скина (вид спереди) и плаща."""
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from .theme import tm


def compose_front(img):
    """Вид спереди из текстуры скина 64×64 (в т.ч. тонкие руки и HD) или старой 64×32."""
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    k = max(1, img.width() // 64)
    legacy = img.height() < img.width()
    slim = (not legacy) and img.pixelColor(55 * k, 20 * k).alpha() == 0
    aw = 3 if slim else 4
    out = QImage(16 * k, 32 * k, QImage.Format.Format_ARGB32)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)

    def part(sx, sy, w, h, dx, dy, mirror=False):
        piece = img.copy(sx * k, sy * k, w * k, h * k)
        if mirror:
            piece = piece.mirrored(True, False)
        p.drawImage(dx * k, dy * k, piece)

    part(8, 8, 8, 8, 4, 0)       # голова
    part(20, 20, 8, 12, 4, 8)    # тело
    if legacy:
        part(44, 20, aw, 12, 4 - aw, 8)
        part(44, 20, aw, 12, 12, 8, True)
        part(4, 20, 4, 12, 4, 20)
        part(4, 20, 4, 12, 8, 20, True)
    else:
        part(44, 20, aw, 12, 4 - aw, 8)   # правая рука (слева от зрителя)
        part(36, 52, aw, 12, 12, 8)       # левая рука
        part(4, 20, 4, 12, 4, 20)         # правая нога
        part(20, 52, 4, 12, 8, 20)        # левая нога
        part(20, 36, 8, 12, 4, 8)         # куртка
        part(44, 36, aw, 12, 4 - aw, 8)   # рукава
        part(52, 52, aw, 12, 12, 8)
        part(4, 36, 4, 12, 4, 20)         # штаны
        part(4, 52, 4, 12, 8, 20)
    part(40, 8, 8, 8, 4, 0)      # шапка/волосы второго слоя
    p.end()
    return out


class SkinPreview(QWidget):
    SS, CS = 10, 12  # масштаб скина и плаща

    def __init__(self):
        super().__init__()
        self.skin = self.cape = None
        self.setMinimumSize(380, 360)

    def set_images(self, skin, cape):
        self.skin, self.cape = skin, cape
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        pal = tm.p
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(pal.border), 1))
        p.setBrush(QColor(pal.surface2))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 14, 14)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        S, CS = self.SS, self.CS
        x0, y0 = 30, (self.height() - 32 * S) // 2
        p.setPen(QColor(pal.text2))
        if self.skin is not None:
            p.drawImage(QRectF(x0, y0, 16 * S, 32 * S), compose_front(self.skin))
        else:
            p.drawText(QRectF(x0, y0, 16 * S, 32 * S), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       "Скина нет\nВ игре будет стандартный")
        cx = x0 + 16 * S + 40
        if self.cape is not None:
            k = self.cape.width() // 64 if self.cape.width() >= 64 else 1
            piece = self.cape.convertToFormat(QImage.Format.Format_ARGB32).copy(k, k, 10 * k, 16 * k)
            p.drawImage(QRectF(cx, y0, 10 * CS, 16 * CS), piece)
        else:
            p.drawText(QRectF(cx, y0, 10 * CS, 16 * CS), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       "Плаща нет")
