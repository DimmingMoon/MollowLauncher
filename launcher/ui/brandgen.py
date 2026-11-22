"""Рисует картинки для главного меню игры: логотип «иконка + MOLLOWLAUNCHER» вместо надписи Minecraft
(рендер в GUI-потоке, при каждом старте лаунчера)."""
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter

from .. import paths
from . import icons

K = 4  # во сколько раз рисуем крупнее, чем размер текстуры в игре (256×64): чётче при любом масштабе GUI
NAME = "MOLLOWLAUNCHER"


def _logo():
    """Логотип 256×44 (в текстуре 256×64): иконка слева, название справа."""
    img = QImage(256 * K, 64 * K, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    f = QFont()
    f.setBold(True)
    f.setWeight(QFont.Weight.Black)
    size = 30 * K
    while True:  # подбираем размер шрифта, чтобы название поместилось
        f.setPixelSize(size)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5 * K)
        tw = QFontMetrics(f).horizontalAdvance(NAME)
        if tw <= 206 * K or size <= 8 * K:
            break
        size -= K // 2 or 1
    icon_px = 40 * K
    gap = 6 * K
    total = icon_px + gap + tw
    x0 = (256 * K - total) // 2
    p.drawPixmap(QRect(x0, 2 * K, icon_px, icon_px), icons.logo(icon_px // 2, "#20C878"))
    r = QRect(x0 + icon_px + gap, 0, tw + 4 * K, 44 * K)
    flags = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
    p.setFont(f)
    p.setPen(QColor(0, 0, 0, 190))  # тень
    p.drawText(r.translated(2 * K, 2 * K), flags, NAME)
    p.setPen(QColor("#F4FFF9"))
    p.drawText(r, flags, NAME)
    p.end()
    return img


def _legacy(logo):
    """Атлас 256×256 для версий до 1.19.3: левая часть (155 px) — сверху слева, правая — на строке v=45."""
    img = QImage(256 * K, 256 * K, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.drawImage(0, 0, logo, 0, 0, 155 * K, 44 * K)
    p.drawImage(0, 45 * K, logo, 155 * K, 0, 101 * K, 44 * K)
    p.end()
    return img


def ensure_assets():
    d = paths.BRAND
    d.mkdir(parents=True, exist_ok=True)
    logo = _logo()
    logo.save(str(d / "logo.png"), "PNG")
    _legacy(logo).save(str(d / "logo_legacy.png"), "PNG")
    empty = QImage(128, 16, QImage.Format.Format_ARGB32)  # edition.png («JAVA EDITION») — пустая
    empty.fill(Qt.GlobalColor.transparent)
    empty.save(str(d / "edition.png"), "PNG")
    icon = QImage(str(paths.resource("assets/icon.png")))
    if not icon.isNull():
        icon.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation).save(str(d / "pack.png"), "PNG")
