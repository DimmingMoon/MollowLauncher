"""Векторные иконки (SVG в коде) — перекрашиваются под текущую тему."""
from PyQt6.QtCore import QByteArray, QPointF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap, QPolygonF
from PyQt6.QtSvg import QSvgRenderer

BODY = {
    "home": '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    "library": '<rect x="3" y="3" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="2"/>'
               '<rect x="3" y="13.5" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2"/>',
    "mods": '<path d="M12 2.5 3.5 7v10L12 21.5 20.5 17V7z"/><path d="M3.5 7 12 11.5 20.5 7M12 11.5v10"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.2 3.6-7 8-7s8 2.8 8 7"/>',
    "settings": '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/>'
                '<circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
    "star": '<path d="m12 2.5 3 6.3 6.9.9-5 4.8 1.3 6.9L12 18l-6.2 3.4 1.3-6.9-5-4.8 6.9-.9z"/>',
    "play": '<path d="M7 4.5v15l12.5-7.5z"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "trash": '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="9" cy="10" r="1.8"/><path d="m21 16-5-5-8 8"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2.5"/>',
    "back": '<path d="M19 12H5M12 5l-7 7 7 7"/>',
    "terminal": '<path d="m4 17 6-6-6-6M12 19h8"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7"/>',
    "copy": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/>',
    "cube": '<path d="M12 2.5 3.5 7v10L12 21.5 20.5 17V7z"/><path d="M3.5 7 12 11.5 20.5 7"/>',
    "puzzle": '<path d="M12 2.5 3.5 7v10L12 21.5 20.5 17V7z"/><path d="M3.5 7 12 11.5 20.5 7M12 11.5v10"/>',
    "download": '<path d="M12 4v11M7 11l5 5 5-5M5 20h14"/>',
    "minimize": '<path d="M5 12h14"/>',
    "maximize": '<rect x="5" y="5" width="14" height="14" rx="1.5"/>',
    "restore": '<rect x="9" y="4.5" width="10.5" height="10.5" rx="1.5"/><path d="M15 15v3a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 4 18v-8a1.5 1.5 0 0 1 1.5-1.5H9"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "tag": '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.2"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "clone": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/>',
}
FILLED = {"star", "play", "stop"}
_cache = {}


def pix(name, color, size=20, filled=None):
    filled = (name in FILLED) if filled is None else filled
    key = (name, color, size, filled)
    if key in _cache:
        return _cache[key]
    fill = color if filled else "none"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{fill}" stroke="{color}" '
           f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{BODY[name]}</svg>')
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(p)
    p.end()
    pm.setDevicePixelRatio(dpr)
    _cache[key] = pm
    return pm


def icon(name, color, size=20, filled=None):
    return QIcon(pix(name, color, size, filled))


def logo(size, primary):
    """Логотип MollowLauncher — изометрический «блок» с полумесяцем."""
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size * dpr
    c = QPointF(s / 2, s / 2)
    k = s * 0.42
    def poly(pts, color):
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([QPointF(c.x() + x * k, c.y() + y * k) for x, y in pts]))
    base = QColor(primary)
    poly([(0, -1), (1, -0.5), (0, 0), (-1, -0.5)], base.lighter(125).name())
    poly([(-1, -0.5), (0, 0), (0, 1.05), (-1, 0.55)], base.darker(135).name())
    poly([(1, -0.5), (0, 0), (0, 1.05), (1, 0.55)], base.darker(175).name())
    # полумесяц в правом верхнем углу
    r = s * 0.13
    mx, my = s * 0.80, s * 0.20
    moon = QPainterPath()
    moon.addEllipse(QPointF(mx, my), r, r)
    cut = QPainterPath()
    cut.addEllipse(QPointF(mx + r * 0.55, my - r * 0.25), r, r)
    p.setBrush(QColor("#F4FFF9"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPath(moon.subtracted(cut))
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm
