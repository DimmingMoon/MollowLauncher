from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget,
)

from ... import java as javamod
from ... import loaders, mojang, net
from ...instance import Instance
from ..widgets import Btn, ProgressBlock, SearchEdit, card_frame, label, scrolled


class InstallPage(QWidget):
    """Создание сборки: выбор версии, загрузчика, проверка Java, установка."""

    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.versions, self.token_l, self.token_j = [], 0, 0
        self.busy = False
        self.java_ok = None

        # --- левая колонка: версии
        lf, ll = card_frame()
        ll.addWidget(label("Версия Minecraft", "h2"))
        self.search = SearchEdit("Поиск версии…")
        self.search.textChanged.connect(self.fill_list)
        self.chk_rel = QCheckBox("Релизы")
        self.chk_rel.setChecked(True)
        self.chk_snap = QCheckBox("Снапшоты")
        self.chk_old = QCheckBox("Старые (alpha/beta)")
        for c in (self.chk_rel, self.chk_snap, self.chk_old):
            c.toggled.connect(self.fill_list)
        row = QHBoxLayout()
        for c in (self.chk_rel, self.chk_snap, self.chk_old):
            row.addWidget(c)
        row.addStretch()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.on_version)
        self.list_msg = label("", "muted", wrap=True)
        self.retry = Btn("Повторить загрузку списка", "refresh")
        self.retry.clicked.connect(self.load_versions)
        self.retry.hide()
        ll.addWidget(self.search)
        ll.addLayout(row)
        ll.addWidget(self.list, 1)
        ll.addWidget(self.list_msg)
        ll.addWidget(self.retry)

        # --- правая колонка: настройки сборки
        rf, rl = card_frame(spacing=10)
        rf.setFixedWidth(440)
        rl.addWidget(label("Новая сборка", "h2"))
        rl.addWidget(label("Название", "muted"))
        self.name = QLineEdit()
        self.name.setPlaceholderText("По умолчанию — версия Minecraft")
        rl.addWidget(self.name)
        rl.addWidget(label("Загрузчик", "muted"))
        lrow = QHBoxLayout()
        self.lgroup = QButtonGroup(self)
        self.lgroup.setExclusive(True)
        self.lbtns = {}
        for ld in loaders.all_loaders():
            b = Btn(ld.label)
            b.setCheckable(True)
            b.setProperty("seg", True)
            b.setChecked(ld.id == "vanilla")
            b.clicked.connect(lambda _=False, k=ld.id: self.on_loader(k))
            self.lgroup.addButton(b)
            self.lbtns[ld.id] = b
            lrow.addWidget(b)
        lrow.addStretch()
        rl.addLayout(lrow)
        self.lv_label = label("Версия загрузчика", "muted")
        self.lv = QComboBox()
        rl.addWidget(self.lv_label)
        rl.addWidget(self.lv)
        rl.addSpacing(6)
        rl.addWidget(label("Требования", "muted"))
        self.req = label("Выберите версию Minecraft", wrap=True)
        rl.addWidget(self.req)
        self.error = label("", "error", wrap=True)
        rl.addWidget(self.error)
        rl.addStretch()
        self.progress = ProgressBlock()
        self.progress.hide()
        rl.addWidget(self.progress)
        self.b_create = Btn("Только создать", "plus")
        self.b_install = Btn("Создать и установить", "download", "primary")
        self.b_cancel = Btn("Отмена", "stop")
        self.b_cancel.hide()
        self.b_create.clicked.connect(lambda: self.create(False))
        self.b_install.clicked.connect(lambda: self.create(True))
        self.b_cancel.clicked.connect(net.CANCEL.set)
        self.b_install.setMinimumHeight(40)
        self.b_create.setMinimumHeight(40)
        self.b_cancel.setMinimumHeight(40)
        rl.addWidget(self.b_install)
        rl.addWidget(self.b_create)
        rl.addWidget(self.b_cancel)

        top = QHBoxLayout()
        back = Btn("Назад", "back", "ghost")
        back.clicked.connect(lambda: ctl.go("library"))
        top.addWidget(back)
        top.addWidget(label("Создать сборку", "h1"))
        top.addStretch()
        mid = QHBoxLayout()
        mid.setSpacing(16)
        right = scrolled(rf)
        right.setFixedWidth(466)
        mid.addWidget(lf, 1)
        mid.addWidget(right)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)
        root.addLayout(top)
        root.addLayout(mid, 1)
        self.update_buttons()

    # --- версии
    def showEvent(self, e):
        super().showEvent(e)
        if not self.versions and not self.busy:
            self.load_versions()

    def load_versions(self):
        self.retry.hide()
        self.list_msg.setText("Загрузка списка версий…")
        self.ctl.run(lambda cb: mojang.manifest()["versions"], self.set_versions, self.versions_failed)

    def versions_failed(self, e):
        self.list_msg.setText(f"Не удалось загрузить список версий: {e}")
        self.retry.show()

    def set_versions(self, versions):
        self.versions = versions
        self.list_msg.setText("")
        self.fill_list()

    def fill_list(self):
        q = self.search.text().strip().lower()
        allowed = set()
        if self.chk_rel.isChecked():
            allowed.add("release")
        if self.chk_snap.isChecked():
            allowed.add("snapshot")
        if self.chk_old.isChecked():
            allowed |= {"old_alpha", "old_beta"}
        keep = self.current_version()
        self.list.blockSignals(True)
        self.list.clear()
        for v in self.versions:
            if v["type"] in allowed and q in v["id"].lower():
                it = QListWidgetItem(v["id"] + ("" if v["type"] == "release" else f"   · {v['type']}"))
                it.setData(Qt.ItemDataRole.UserRole, v["id"])
                self.list.addItem(it)
                if v["id"] == keep:
                    self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)  # вызовет on_version
        else:
            self.on_version()

    def current_version(self):
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def current_loader(self):
        for k, b in self.lbtns.items():
            if b.isChecked():
                return loaders.get(k)
        return loaders.get("vanilla")

    def on_loader(self, _key):
        self.update_loader_versions()

    def on_version(self, *_):
        self.update_loader_versions()
        self.update_java()

    def update_loader_versions(self):
        ld, mc = self.current_loader(), self.current_version()
        self.lv.clear()
        self.error.setText("")
        need = ld.id != "vanilla"
        self.lv.setVisible(need)
        self.lv_label.setVisible(need)
        self.update_buttons()
        if not need or not mc:
            return
        self.token_l += 1
        tok = self.token_l

        def ok(vs):
            if tok != self.token_l:
                return
            self.lv.addItems(vs)
            if not vs:
                self.error.setText(f"{ld.label} не поддерживает Minecraft {mc}")
            self.update_buttons()

        def fail(e):
            if tok == self.token_l:
                self.error.setText(f"Ошибка загрузки версий {ld.label}: {e}")

        self.ctl.run(lambda cb: ld.versions(mc), ok, fail)

    def update_java(self):
        mc = self.current_version()
        self.java_ok = None
        if not mc:
            self.req.setText("Выберите версию Minecraft")
            return
        self.token_j += 1
        tok = self.token_j
        self.req.setText("Проверяю требования…")

        def job(cb):
            vj = mojang.version_json(mc)
            major = vj.get("javaVersion", {}).get("majorVersion", 8)
            return major, javamod.pick(major)

        def ok(res):
            if tok != self.token_j:
                return
            major, found = res
            self.req.setText(f"Minecraft {mc}\nНужна Java {major} — " +
                             (f"найдена:\n{found}" if found else
                              "не найдена. Лаунчер предложит скачать её при установке/запуске."))

        def fail(e):
            if tok == self.token_j:
                self.req.setText(f"Не удалось получить требования версии: {e}")

        self.ctl.run(job, ok, fail)

    def update_buttons(self):
        ready = bool(self.current_version()) and not self.busy and \
            (self.current_loader().id == "vanilla" or bool(self.lv.currentText()))
        self.b_create.setEnabled(ready)
        self.b_install.setEnabled(ready)

    # --- создание / установка
    def create(self, install):
        mc, ld = self.current_version(), self.current_loader()
        if not mc:
            return
        lv = self.lv.currentText() if ld.id != "vanilla" else ""
        if ld.id != "vanilla" and not lv:
            self.error.setText("Нет доступной версии загрузчика")
            return
        name = self.name.text().strip() or mc
        inst = Instance.create(name, mc, ld.id, lv)
        self.ctl.selected_id = inst.id
        self.ctl.refresh_all()
        if not install:
            self.ctl.toast(f"Сборка «{name}» создана")
            self.name.clear()
            self.ctl.go("library")
            return
        self.install(inst, ld, mc, lv)

    def install(self, inst, ld, mc, lv):
        net.reset_stats()
        stages = ([ld.label] if ld.id != "vanilla" else []) + ["Клиент Minecraft", "Библиотеки", "Ресурсы"]
        self.busy = True
        self.error.setText("")
        self.progress.show()
        self.progress.start(stages)
        self.b_cancel.show()
        self.update_buttons()

        def job(cb):
            if ld.id != "vanilla":
                cb(ld.label, 0, 1)
                ld.ensure_profile(mc, lv)
            return mojang.install(inst.version_id, cb)

        def end():
            self.busy = False
            self.b_cancel.hide()
            self.update_buttons()

        def ok(_):
            self.progress.finish(True)
            end()
            self.name.clear()
            self.ctl.toast(f"«{inst.name}» установлена и готова к запуску")
            self.progress.hide()
            self.ctl.go("library")

        def fail(e):
            self.progress.fail()
            end()
            if isinstance(e, net.Cancelled):
                self.error.setText("Установка отменена. Сборка создана — недостающие файлы докачаются при запуске.")
            else:
                self.error.setText(f"Ошибка установки: {type(e).__name__}: {e}\n"
                                   "Сборка создана; попробуйте запустить её позже.")

        self.ctl.run(job, ok, fail, self.progress.on_progress)
