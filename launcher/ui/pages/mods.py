from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ... import mods
from ..widgets import Btn, SearchEdit, ToggleSwitch, card_frame, fmt_bytes, label
from .modbrowser import ModBrowser


class ModsPanel(QWidget):
    """Менеджер модов одной сборки (встроен во вкладку настроек сборки)."""

    def __init__(self, ctl):
        super().__init__()
        self.ctl, self.inst, self.items = ctl, None, []
        self.search = SearchEdit("Поиск модов…")
        self.search.textChanged.connect(self.apply_filter)
        find = Btn("Найти моды", "search", "primary")
        find.clicked.connect(self.open_browser)
        add = Btn("Из файла…", "plus")
        add.setToolTip("Добавить .jar с компьютера")
        add.clicked.connect(self.add)
        folder = Btn("Папка", "folder")
        folder.clicked.connect(self.open_folder)
        refresh = Btn("", "refresh")
        refresh.setToolTip("Обновить список")
        refresh.clicked.connect(self.reload)
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(self.search, 1)
        top.addWidget(find)
        top.addWidget(add)
        top.addWidget(folder)
        top.addWidget(refresh)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["", "Мод", "Версия", "Загрузчик", "Размер"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        h = self.table.horizontalHeader()
        h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 64)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in (2, 3, 4):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.show_details)
        self.status = label("", "muted")

        left = QVBoxLayout()
        left.addLayout(top)
        left.addWidget(self.table, 1)
        left.addWidget(self.status)

        self.panel, pl = card_frame(spacing=8)
        self.panel.setFixedWidth(280)
        self.d_name = label("Выберите мод", "h2", wrap=True)
        self.d_meta = label("", "muted", wrap=True)
        self.d_desc = label("", wrap=True)
        self.d_file = label("", "muted", wrap=True)
        for w in (self.d_name, self.d_meta, self.d_desc):
            pl.addWidget(w)
        pl.addStretch()
        pl.addWidget(self.d_file)
        self.del_btn = Btn("Удалить файл мода", "trash", "danger")
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self.delete)
        pl.addWidget(self.del_btn)

        self.list_view = QWidget()
        lv = QHBoxLayout(self.list_view)
        lv.setContentsMargins(0, 12, 0, 0)
        lv.setSpacing(16)
        lv.addLayout(left, 1)
        lv.addWidget(self.panel)

        self.browser = ModBrowser(ctl, self.after_install)
        self.browser.back.connect(self.show_list)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.list_view)
        self.stack.addWidget(self.browser)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stack)

    def open_browser(self):
        if self.inst:
            self.browser.open(self.inst)
            self.stack.setCurrentIndex(1)

    def show_list(self):
        self.reload()
        self.stack.setCurrentIndex(0)

    def after_install(self):
        self.reload()
        self.ctl.refresh_cards()

    def load(self, inst):
        self.stack.setCurrentIndex(0)
        self.inst = inst
        self.search.clear()
        self.reload()

    def reload(self):
        self.table.setRowCount(0)
        self.items = []
        self.show_details()
        if not self.inst:
            return
        self.items = mods.list_mods(self.inst)
        self.table.setRowCount(len(self.items))
        for r, m in enumerate(self.items):
            sw = ToggleSwitch(m.enabled)
            sw.toggled.connect(lambda on, mod=m, s=sw: self.toggle(mod, on, s))
            holder = QWidget()
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(sw, 0, Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(r, 0, holder)
            self.table.setItem(r, 1, QTableWidgetItem(m.name))
            self.table.setItem(r, 2, QTableWidgetItem(m.version or "—"))
            self.table.setItem(r, 3, QTableWidgetItem(m.kind))
            self.table.setItem(r, 4, QTableWidgetItem(fmt_bytes(m.size)))
            self.table.setRowHeight(r, 46)
        self.apply_filter()
        self.update_status()

    def update_status(self):
        off = sum(1 for m in self.items if not m.enabled)
        self.status.setText(f"Модов: {len(self.items)} · отключено: {off}" if self.items
                            else "Модов пока нет — нажмите «Добавить моды».")

    def apply_filter(self):
        q = self.search.text().strip().lower()
        for r, m in enumerate(self.items):
            hay = f"{m.name} {m.mod_id} {m.filename} {m.authors}".lower()
            self.table.setRowHidden(r, bool(q) and q not in hay)

    def toggle(self, mod, on, switch):
        try:
            mods.set_enabled(mod, on)
        except (OSError, FileExistsError) as e:
            switch.blockSignals(True)
            switch.setChecked(not on)
            switch.blockSignals(False)
            self.ctl.toast(f"Не удалось переключить мод: {e}", "error")
            return
        self.update_status()
        self.show_details()
        self.ctl.refresh_cards()

    def current(self):
        r = self.table.currentRow()
        return self.items[r] if 0 <= r < len(self.items) else None

    def show_details(self):
        m = self.current()
        self.del_btn.setEnabled(bool(m))
        if not m:
            self.d_name.setText("Выберите мод")
            for w in (self.d_meta, self.d_desc, self.d_file):
                w.setText("")
            return
        self.d_name.setText(m.name)
        meta = [f"Версия: {m.version or '—'}", f"Загрузчик: {m.kind}"]
        if m.mod_id:
            meta.append(f"ID: {m.mod_id}")
        if m.authors:
            meta.append(f"Авторы: {m.authors}")
        meta.append("Статус: " + ("включён" if m.enabled else "отключён"))
        self.d_meta.setText("\n".join(meta))
        self.d_desc.setText(m.description or "Описание отсутствует")
        self.d_file.setText(f"Файл: {m.filename}\nРазмер: {fmt_bytes(m.size)}")

    def add(self):
        if not self.inst:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите моды", "", "Моды (*.jar)")
        if files:
            added = mods.add_mods(self.inst, files)
            self.ctl.toast(f"Добавлено модов: {len(added)}")
            self.reload()
            self.ctl.refresh_cards()

    def open_folder(self):
        if self.inst:
            self.inst.mods_dir.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.inst.mods_dir)))

    def delete(self):
        m = self.current()
        if not m:
            return

        def do():
            try:
                mods.delete_mod(m)
            except OSError as e:
                self.ctl.toast(f"Не удалось удалить: {e}", "error")
                return
            self.reload()
            self.ctl.refresh_cards()

        self.ctl.confirm("Удалить мод?",
                         f"Файл «{m.filename}» будет удалён с диска без возможности восстановления.\n"
                         "Чтобы просто выключить мод, используйте переключатель.",
                         do, "Удалить", danger=True)
