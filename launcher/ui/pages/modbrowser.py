"""Каталог модов Modrinth внутри лаунчера (вкладка «Моды» настроек сборки)."""
import hashlib

from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ... import modrinth, net
from ..widgets import Btn, ElidedLabel, MenuButton, SearchEdit, label, scrolled

ICON = 52


def placeholder(title):
    h = int(hashlib.md5(title.encode()).hexdigest()[:6], 16)
    pm = QPixmap(ICON, ICON)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor.fromHsv(h % 360, 140, 160))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, ICON, ICON, 12, 12)
    p.setPen(QColor("white"))
    f = QFont()
    f.setBold(True)
    f.setPointSize(16)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, (title[:1] or "?").upper())
    p.end()
    return pm


def rounded(pm):
    pm = pm.scaled(ICON, ICON, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    out = QPixmap(ICON, ICON)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    from PyQt6.QtGui import QPainterPath
    path = QPainterPath()
    path.addRoundedRect(0, 0, ICON, ICON, 12, 12)
    p.setClipPath(path)
    p.drawPixmap((ICON - pm.width()) // 2, (ICON - pm.height()) // 2, pm)
    p.end()
    return out


class IconLoader(QThread):
    loaded = pyqtSignal(int, bytes)

    def __init__(self, items):
        super().__init__()
        self.items, self._stop = items, False

    def stop(self):
        self._stop = True

    def run(self):
        for idx, url in self.items:
            if self._stop:
                return
            try:
                r = net.S.get(url, timeout=15)
                if r.ok:
                    self.loaded.emit(idx, r.content)
            except Exception:
                pass


class ResultRow(QFrame):
    install = pyqtSignal(object)

    def __init__(self, hit, installed):
        super().__init__()
        self.hit = hit
        self.setProperty("card", True)
        self.icon = QLabel()
        self.icon.setFixedSize(ICON, ICON)
        self.icon.setPixmap(placeholder(hit["title"]))
        title = ElidedLabel(hit["title"])
        title.setProperty("role", "h3")
        dl = hit.get("downloads", 0)
        meta = label(f"{hit.get('author', '')}  ·  {dl:,} скачиваний".replace(",", " "), "muted")
        desc = ElidedLabel(hit.get("description", ""))
        desc.setProperty("role", "muted")
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(title)
        col.addWidget(meta)
        col.addWidget(desc)
        self.btn = Btn("", "download", size=16)
        self.btn.setFixedWidth(150)
        self.btn.clicked.connect(lambda: self.install.emit(self))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(14)
        lay.addWidget(self.icon)
        lay.addLayout(col, 1)
        lay.addWidget(self.btn)
        self.set_state("installed" if installed else "idle")

    def set_icon(self, data):
        pm = QPixmap()
        if pm.loadFromData(data):
            self.icon.setPixmap(rounded(pm))

    def set_state(self, state):
        self.btn.setEnabled(state == "idle")
        self.btn.setText({"idle": "Установить", "busy": "Установка…", "installed": "Установлен"}[state])
        self.btn.icon_name = {"idle": "download", "busy": "refresh", "installed": "check"}[state]
        self.btn.set_variant("primary" if state == "idle" else "secondary")


class ModBrowser(QWidget):
    back = pyqtSignal()

    def __init__(self, ctl, on_installed):
        super().__init__()
        self.ctl, self.on_installed = ctl, on_installed
        self.inst, self.rows, self.offset, self.total = None, [], 0, 0
        self.token, self.loader = 0, None
        self.installed = set()

        b = Btn("К установленным", "back", "ghost")
        b.clicked.connect(self.back.emit)
        self.query = SearchEdit("Поиск модов на Modrinth…")
        self.query.returnPressed.connect(self.new_search)
        self.sort = MenuButton("Сортировка", modrinth.SORTS, "relevance")
        self.sort.changed.connect(lambda _: self.new_search())
        go = Btn("Найти", "search", "primary", 16)
        go.clicked.connect(self.new_search)
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(b)
        top.addWidget(self.query, 1)
        top.addWidget(self.sort)
        top.addWidget(go)

        self.note = label("", "muted", wrap=True)
        self.host = QWidget()
        self.list = QVBoxLayout(self.host)
        self.list.setContentsMargins(0, 0, 8, 0)
        self.list.setSpacing(10)
        self.list.addStretch()
        self.more = Btn("Показать ещё", "plus")
        self.more.clicked.connect(self.load_more)
        self.more.hide()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 10, 0, 0)
        root.setSpacing(10)
        root.addLayout(top)
        root.addWidget(self.note)
        root.addWidget(scrolled(self.host), 1)
        root.addWidget(self.more, 0, Qt.AlignmentFlag.AlignHCenter)

    def open(self, inst):
        self.inst = inst
        self.installed = modrinth.installed_ids(inst)
        loader = inst.data["loader"]
        ok = modrinth.supported(loader)
        for w in (self.query, self.sort):
            w.setEnabled(ok)
        self.clear()
        if not ok:
            self.note.setText("Сборка Vanilla не поддерживает моды. Создайте сборку с загрузчиком Fabric "
                              "(Библиотека → Создать сборку).")
            return
        self.query.clear()
        self.new_search()

    def clear(self):
        if self.loader:
            self.loader.stop()
        for r in self.rows:
            r.hide()
            r.deleteLater()
        self.rows, self.offset, self.total = [], 0, 0
        self.more.hide()

    def new_search(self):
        if not self.inst or not modrinth.supported(self.inst.data["loader"]):
            return
        self.clear()
        self.fetch()

    def load_more(self):
        self.fetch()

    def fetch(self):
        inst = self.inst
        self.token += 1
        tok = self.token
        q, sort, off = self.query.text().strip(), self.sort.current, self.offset
        self.note.setText("Загрузка…")
        self.more.setEnabled(False)

        def ok(res):
            if tok != self.token:
                return
            hits, total = res
            self.total = total
            self.note.setText(f"Minecraft {inst.data['mc_version']} · {inst.loader_label} · найдено: {total}"
                              if total else "Ничего не найдено для этой версии и загрузчика")
            start = len(self.rows)
            for h in hits:
                row = ResultRow(h, h["project_id"] in self.installed)
                row.install.connect(self.do_install)
                self.list.insertWidget(self.list.count() - 1, row)
                self.rows.append(row)
            self.offset = off + len(hits)
            self.more.setEnabled(True)
            self.more.setVisible(self.offset < total)
            items = [(start + i, h["icon_url"]) for i, h in enumerate(hits) if h.get("icon_url")]
            if items:
                ld = IconLoader(items)
                ld.loaded.connect(lambda i, data, ld=ld: self._icon(ld, i, data))
                ld.finished.connect(ld.deleteLater)
                if self.loader:
                    self.loader.stop()
                self.loader = ld
                ld.start()

        def fail(e):
            if tok == self.token:
                self.note.setText(f"Не удалось загрузить каталог: {e}. Проверьте подключение к интернету.")
                self.more.setEnabled(True)

        self.ctl.run(lambda cb: modrinth.search(q, inst.data["mc_version"], inst.data["loader"], sort, off), ok, fail)

    def _icon(self, ld, idx, data):
        if ld is self.loader and idx < len(self.rows):
            self.rows[idx].set_icon(data)

    def do_install(self, row):
        inst, hit = self.inst, row.hit
        row.set_state("busy")
        net.reset_stats()

        def ok(ctx):
            row.set_state("installed")
            self.installed.add(hit["project_id"])
            for pid, _f in ctx["done"]:
                self.installed.add(pid)
            extra = len(ctx["done"]) - 1
            msg = f"«{hit['title']}» установлен" + (f" (+{extra} завис.)" if extra > 0 else "")
            self.ctl.toast(msg + (" · есть предупреждения" if ctx["warn"] else ""))
            self.on_installed()

        def fail(e):
            row.set_state("idle")
            self.ctl.toast(f"Не удалось установить: {e}", "error")

        self.ctl.run(lambda cb: modrinth.install(inst, hit["project_id"], hit["title"]), ok, fail)
