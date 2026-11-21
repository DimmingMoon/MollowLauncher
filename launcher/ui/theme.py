"""Theme Management: палитры, генерация QSS, сохранение выбора в конфигурации."""
from dataclasses import dataclass
from string import Template

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication

from .. import paths


@dataclass(frozen=True)
class Palette:
    id: str
    label: str
    bg: str
    surface: str
    surface2: str
    primary: str
    primary_hover: str
    text: str
    text2: str
    border: str
    on_primary: str
    danger: str = "#E5534B"


PALETTES = {
    "emerald": Palette("emerald", "Emerald", "#101411", "#181F1A", "#202A23", "#20C878", "#35DF91",
                       "#F1F5F2", "#91A398", "#2B3A30", "#05140C"),
    "purple": Palette("purple", "Purple", "#110F18", "#1A1724", "#241F33", "#9B6BFF", "#B28CFF",
                      "#F3F0FA", "#A39BB8", "#352E4A", "#12081F"),
    "blue": Palette("blue", "Blue", "#0E1218", "#151B24", "#1D2632", "#3D8BFD", "#6AA5FF",
                    "#EEF3FA", "#93A1B5", "#2A3648", "#06101F"),
    "monochrome": Palette("monochrome", "Monochrome", "#111111", "#1A1A1A", "#242424", "#E6E6E6",
                          "#FFFFFF", "#F2F2F2", "#9A9A9A", "#333333", "#111111"),
}


def qc(hex_color, alpha=255):
    c = QColor(hex_color)
    c.setAlpha(alpha)
    return c


def mix(a, b, t):
    ca, cb = QColor(a), QColor(b)
    return QColor(int(ca.red() + (cb.red() - ca.red()) * t),
                  int(ca.green() + (cb.green() - ca.green()) * t),
                  int(ca.blue() + (cb.blue() - ca.blue()) * t))


def rgba(hex_color, a):
    c = QColor(hex_color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{a})"


QSS = Template("""
* { font-family: "Segoe UI Variable", "Segoe UI", "Ubuntu", sans-serif; font-size: 10pt; color: $text; }
QWidget { background: transparent; }
QMainWindow, QDialog, #Root { background: $bg; }
#Sidebar { background: $surface; border-right: 1px solid $border; }
QLabel { background: transparent; }
#TitleBar { background: $surface; border-bottom: 1px solid $border; }
QToolButton[wbtn] { border-radius: 0px; padding: 0px; }
QToolButton[wbtn]:hover { background: $surface2; }
QToolButton[wbtn="close"]:hover { background: $danger; }
QPushButton[acc="true"] { text-align: left; padding: 8px 12px; background: $surface2; border: 1px solid $border;
    border-radius: 12px; font-weight: 600; }
QPushButton[acc="true"]:hover { border-color: $primary; }
QLabel[role="h1"] { font-size: 22pt; font-weight: 700; }
QLabel[role="h2"] { font-size: 14pt; font-weight: 600; }
QLabel[role="h3"] { font-size: 11pt; font-weight: 600; }
QLabel[role="muted"] { color: $text2; }
QLabel[role="error"] { color: $danger; }
QLabel[role="chip"] { background: $primary_soft; color: $primary; border-radius: 10px; padding: 2px 10px; font-weight: 600; }
QFrame[card="true"] { background: $surface; border: 1px solid $border; border-radius: 14px; }
QFrame[card="true"][active="true"] { border: 1px solid $primary; }
QFrame[card="true"][clickable="true"]:hover { border: 1px solid $text2; }
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
    background: $surface2; border: 1px solid $border; border-radius: 10px; padding: 7px 10px;
    selection-background-color: $primary; selection-color: $on_primary; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus { border: 1px solid $primary; }
QSpinBox::up-button, QSpinBox::down-button { width: 0px; border: none; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox::down-arrow { image: url($arrow); width: 12px; height: 12px; }
QComboBox QAbstractItemView { background: $surface2; border: 1px solid $border; outline: 0; padding: 4px;
    selection-background-color: $primary_soft; selection-color: $text; }
QPushButton { background: $surface2; border: 1px solid $border; border-radius: 10px; padding: 8px 16px; font-weight: 600; }
QPushButton:hover { border-color: $primary; }
QPushButton:disabled { color: $text2; background: $surface; border-color: $border; }
QPushButton[variant="primary"] { background: $primary; color: $on_primary; border: 1px solid $primary; }
QPushButton[variant="primary"]:hover { background: $primary_hover; border-color: $primary_hover; }
QPushButton[variant="primary"]:disabled { background: $surface2; color: $text2; border-color: $border; }
QPushButton[variant="danger_fill"] { background: $danger; color: #ffffff; border: 1px solid $danger; }
QPushButton[variant="danger_fill"]:hover { background: #F0716A; border-color: #F0716A; }
QPushButton[variant="ghost"] { background: transparent; border: 1px solid transparent; }
QPushButton[variant="ghost"]:hover { background: $surface2; }
QPushButton[variant="danger"]:hover { border-color: $danger; color: $danger; }
QPushButton, QToolButton { outline: 0; }
QPushButton::menu-indicator { image: none; width: 0px; }
QPushButton[nav="true"] { text-align: left; padding: 11px 14px; border: none; background: transparent;
    color: $text2; font-size: 10.5pt; border-radius: 12px; }
QPushButton[nav="true"]:hover { background: $surface2; color: $text; }
QPushButton[nav="true"]:checked { background: $primary_soft; color: $primary; }
QPushButton[seg="true"]:checked { background: $primary_soft; border: 1px solid $primary; color: $primary; }
QToolButton { background: transparent; border: none; border-radius: 10px; padding: 6px; }
QToolButton:hover { background: $surface2; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $border; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: $text2; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: $border; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QToolTip { background: $surface2; color: $text; border: 1px solid $border; padding: 4px 8px; }
QMenu { background: $surface2; border: 1px solid $border; border-radius: 10px; padding: 6px; }
QMenu::item { padding: 7px 24px 7px 14px; border-radius: 6px; }
QMenu::item:selected { background: $primary_soft; }
QMenu::item:disabled { color: $text2; }
QMenu::separator { height: 1px; background: $border; margin: 5px 8px; }
QProgressBar { background: $surface2; border: none; border-radius: 5px; max-height: 10px; min-height: 10px; color: transparent; }
QProgressBar::chunk { background: $primary; border-radius: 5px; }
QTableWidget { background: transparent; border: none; outline: 0; gridline-color: transparent;
    selection-background-color: $primary_soft; }
QTableWidget::item { padding: 6px 10px; border-bottom: 1px solid $border; }
QTableWidget::item:selected { background: $primary_soft; color: $text; }
QHeaderView::section { background: transparent; color: $text2; border: none; border-bottom: 1px solid $border;
    padding: 8px 10px; font-weight: 600; }
QListWidget { background: transparent; border: none; outline: 0; }
QListWidget::item { padding: 8px 10px; border-radius: 8px; }
QListWidget::item:hover { background: $surface2; }
QListWidget::item:selected { background: $primary_soft; color: $text; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid $border; background: $surface2; }
QCheckBox::indicator:checked { background: $primary; border-color: $primary; image: url($check); }
QTabWidget::pane { border: none; border-top: 1px solid $border; top: -1px; }
QTabBar::tab { background: transparent; padding: 9px 18px; margin-right: 6px; color: $text2; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: $primary; border-bottom: 2px solid $primary; }
""")


class ThemeManager(QObject):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.p = PALETTES["emerald"]
        self.cfg = None

    def init(self, cfg):
        self.cfg = cfg
        self.p = PALETTES.get(cfg["theme"], PALETTES["emerald"])

    def set(self, theme_id):
        if theme_id not in PALETTES:
            return
        self.p = PALETTES[theme_id]
        if self.cfg is not None:
            self.cfg["theme"] = theme_id
            self.cfg.save()
        self.apply()
        self.changed.emit()

    def _assets(self):
        paths.CACHE.mkdir(parents=True, exist_ok=True)
        arrow = paths.CACHE / f"arrow_{self.p.id}.png"
        pm = QPixmap(24, 24)
        pm.fill(QColor(0, 0, 0, 0))
        g = QPainter(pm)
        g.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(self.p.text2), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        g.setPen(pen)
        g.drawLine(5, 9, 12, 16)
        g.drawLine(12, 16, 19, 9)
        g.end()
        pm.save(str(arrow))
        check = paths.CACHE / f"check_{self.p.id}.png"
        pm = QPixmap(24, 24)
        pm.fill(QColor(0, 0, 0, 0))
        g = QPainter(pm)
        g.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(self.p.on_primary), 3.4)
        g.setPen(pen)
        g.drawLine(5, 12, 10, 17)
        g.drawLine(10, 17, 19, 7)
        g.end()
        pm.save(str(check))
        return arrow.as_posix(), check.as_posix()

    def stylesheet(self):
        p = self.p
        arrow, check = self._assets()
        return QSS.safe_substitute(
            bg=p.bg, surface=p.surface, surface2=p.surface2, primary=p.primary,
            primary_hover=p.primary_hover, text=p.text, text2=p.text2, border=p.border,
            on_primary=p.on_primary, danger=p.danger, primary_soft=rgba(p.primary, 46),
            arrow=arrow, check=check)

    def apply(self):
        app = QApplication.instance()
        if app:
            app.setStyleSheet(self.stylesheet())


tm = ThemeManager()


def repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()
