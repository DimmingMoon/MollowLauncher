from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QVBoxLayout, QWidget,
)

from ... import java as javamod
from ... import net, paths
from ..theme import PALETTES, tm
from ..widgets import Btn, NumberEdit, ProgressBlock, card_frame, label, scrolled


def _spin(value, lo, hi, step=1):
    return NumberEdit(value, lo, hi)


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


class SettingsPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        cfg = ctl.cfg
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 8, 0)
        bl.setSpacing(14)

        # --- тема
        f, l = card_frame()
        l.addWidget(label("Внешний вид", "h2"))
        row = QHBoxLayout()
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.theme_btns = {}
        for pid, pal in PALETTES.items():
            b = Btn(pal.label)
            b.setCheckable(True)
            b.setProperty("seg", True)
            b.setIcon(_dot(pal.primary))
            b.setChecked(pid == tm.p.id)
            b.clicked.connect(lambda _=False, k=pid: tm.set(k))
            self.group.addButton(b)
            self.theme_btns[pid] = b
            row.addWidget(b)
        row.addStretch()
        l.addLayout(row)
        bl.addWidget(f)

        # --- запуск
        f, l = card_frame()
        l.addWidget(label("Запуск игры (значения по умолчанию)", "h2"))
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.java = QLineEdit(cfg["java_path"])
        self.java.setPlaceholderText("Авто — подбирается под версию игры")
        jb = Btn("Обзор…")
        jb.clicked.connect(self.browse)
        jr = QHBoxLayout()
        jr.addWidget(self.java, 1)
        jr.addWidget(jb)
        self.minm = _spin(cfg["min_mem"], 128, 65536, 256)
        self.maxm = _spin(cfg["max_mem"], 256, 65536, 256)
        self.jvm = QLineEdit(cfg["jvm_args"])
        self.w = _spin(cfg["width"], 100, 10000, 1)
        self.h = _spin(cfg["height"], 100, 10000, 1)
        form.addRow("Java", jr)
        form.addRow("Мин. память, МБ", self.minm)
        form.addRow("Макс. память, МБ", self.maxm)
        form.addRow("JVM-аргументы", self.jvm)
        form.addRow("Ширина окна", self.w)
        form.addRow("Высота окна", self.h)
        l.addLayout(form)
        save = Btn("Сохранить", "check", "primary")
        save.clicked.connect(self.save)
        sr = QHBoxLayout()
        sr.addWidget(save)
        sr.addStretch()
        l.addLayout(sr)
        bl.addWidget(f)

        # --- Java
        f, l = card_frame()
        l.addWidget(label("Java", "h2"))
        scan = Btn("Найти установленные Java", "search")
        scan.clicked.connect(self.scan)
        self.found = QListWidget()
        self.found.setMaximumHeight(110)
        self.found.itemDoubleClicked.connect(lambda it: self.java.setText(it.data(Qt.ItemDataRole.UserRole)))
        l.addWidget(scan)
        l.addWidget(self.found)
        l.addWidget(label("Двойной клик по найденной Java подставит путь в поле выше (затем «Сохранить»).",
                          "muted", wrap=True))
        dl = QHBoxLayout()
        self.dl_btns = []
        for m in (8, 17, 21):
            b = Btn(f"Скачать Java {m}", "download")
            b.clicked.connect(lambda _=False, mm=m: self.download(mm))
            self.dl_btns.append(b)
            dl.addWidget(b)
        dl.addStretch()
        l.addLayout(dl)
        self.progress = ProgressBlock()
        self.progress.hide()
        self.cancel = Btn("Отмена", "stop")
        self.cancel.hide()
        self.cancel.clicked.connect(net.CANCEL.set)
        l.addWidget(self.progress)
        l.addWidget(self.cancel)
        bl.addWidget(f)

        # --- данные
        f, l = card_frame()
        l.addWidget(label("Данные", "h2"))
        l.addWidget(label(str(paths.DATA), "muted", wrap=True))
        ob = Btn("Открыть папку данных", "folder")
        ob.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.DATA))))
        r = QHBoxLayout()
        r.addWidget(ob)
        r.addStretch()
        l.addLayout(r)
        bl.addWidget(f)
        bl.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 20, 20)
        root.setSpacing(14)
        root.addWidget(label("Настройки", "h1"))
        root.addWidget(scrolled(body), 1)

    def refresh(self):
        self.theme_btns[tm.p.id].setChecked(True)

    def browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "Выберите java / javaw")
        if p:
            self.java.setText(p)

    def save(self):
        c = self.ctl.cfg
        c["java_path"] = self.java.text().strip()
        c["min_mem"], c["max_mem"] = self.minm.value(), self.maxm.value()
        c["jvm_args"] = self.jvm.text().strip()
        c["width"], c["height"] = self.w.value(), self.h.value()
        c.save()
        self.ctl.toast("Настройки сохранены")

    def scan(self):
        self.found.clear()
        self.found.addItem("Поиск…")

        def done(infos):
            self.found.clear()
            for p, m in infos:
                it = QListWidgetItem(f"Java {m} — {p}")
                it.setData(Qt.ItemDataRole.UserRole, p)
                self.found.addItem(it)
            if not infos:
                self.found.addItem("Ничего не найдено — нажмите «Скачать Java»")

        self.ctl.run(lambda cb: javamod.find_all(), done)

    def download(self, major):
        net.reset_stats()
        self.progress.show()
        self.cancel.show()
        for b in self.dl_btns:
            b.setEnabled(False)
        self.progress.start([f"Скачивание Java {major}", f"Распаковка Java {major}"])

        def end():
            self.cancel.hide()
            for b in self.dl_btns:
                b.setEnabled(True)

        def ok(path):
            self.progress.finish(True)
            end()
            self.ctl.toast(f"Java {major} установлена")
            self.scan()

        def fail(e):
            self.progress.fail()
            end()
            if isinstance(e, net.Cancelled):
                self.ctl.toast("Скачивание отменено")
            else:
                self.ctl.toast(f"Ошибка: {e}", "error")

        self.ctl.run(lambda cb: javamod.download_java(major, cb), ok, fail, self.progress.on_progress)
