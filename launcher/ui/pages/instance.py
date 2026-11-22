from PyQt6.QtCore import Qt
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QTabWidget, QToolButton, QVBoxLayout, QWidget,
)

from ... import covers

from ..widgets import Btn, card_frame, label, scrolled
from .mods import ModsPanel


class InstancePage(QWidget):
    """Настройки сборки: вкладки «Основное» и «Моды» (страница внутри окна, не диалог).
    Память и размер окна задаются только в общих настройках."""

    def __init__(self, ctl):
        super().__init__()
        self.ctl, self.inst = ctl, None
        self.title = label("Настройки сборки", "h1")
        self.ver = label("", "muted")
        self.name = QLineEdit()
        self.java = QLineEdit()
        self.java.setPlaceholderText("Авто (общая настройка)")
        jb = Btn("Обзор…")
        jb.clicked.connect(self.browse)
        jr = QHBoxLayout()
        jr.addWidget(self.java, 1)
        jr.addWidget(jb)
        self.jvm = QLineEdit()
        self.jvm.setPlaceholderText("Например: -XX:+UseG1GC")

        f, l = card_frame()
        l.addWidget(label("Сборка", "h2"))
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.addRow("Название", self.name)
        form.addRow("Java", jr)
        form.addRow("Доп. JVM-аргументы", self.jvm)
        l.addLayout(form)

        cf, cl = card_frame()
        cl.addWidget(label("Обложка", "h2"))
        cl.addWidget(label("Стандартные обложки — выберите любую; потом её можно заменить своим изображением.",
                           "muted", wrap=True))
        prow = QHBoxLayout()
        prow.setSpacing(8)
        for i, (nm, _) in enumerate(covers.PRESETS):
            pb = QToolButton()
            pb.setProperty("thumb", True)
            pb.setIcon(QIcon(covers.preset_pixmap(i, 112, 63)))
            pb.setIconSize(QSize(112, 63))
            pb.setFixedSize(122, 73)
            pb.setToolTip(nm)
            pb.setCursor(Qt.CursorShape.PointingHandCursor)
            pb.clicked.connect(lambda _=False, k=i: self.preset(k))
            prow.addWidget(pb)
        prow.addStretch()
        cl.addLayout(prow)
        cb = Btn("Сменить обложку…", "image")
        cr = Btn("Стандартная обложка", "refresh")
        cb.clicked.connect(lambda: self.inst and ctl.change_cover(self.inst))
        cr.clicked.connect(lambda: self.inst and ctl.reset_cover(self.inst))
        row = QHBoxLayout()
        row.addWidget(cb)
        row.addWidget(cr)
        row.addStretch()
        cl.addLayout(row)

        save = Btn("Сохранить", "check", "primary")
        cancel = Btn("Назад")
        save.clicked.connect(self.save)
        cancel.clicked.connect(lambda: ctl.go("library"))
        btns = QHBoxLayout()
        btns.addWidget(save)
        btns.addWidget(cancel)
        btns.addStretch()

        general = QWidget()
        gl = QVBoxLayout(general)
        gl.setContentsMargins(0, 12, 8, 0)
        gl.setSpacing(14)
        gl.addWidget(f)
        gl.addWidget(cf)
        gl.addLayout(btns)
        gl.addStretch()

        self.mods = ModsPanel(ctl)
        self.tabs = QTabWidget()
        self.tabs.addTab(scrolled(general), "Основное")
        self.tabs.addTab(self.mods, "Моды")

        back = Btn("Назад", "back", "ghost")
        back.clicked.connect(lambda: ctl.go("library"))
        top = QHBoxLayout()
        top.addWidget(back)
        top.addWidget(self.title)
        top.addStretch()
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(10)
        root.addLayout(top)
        root.addWidget(self.ver)
        root.addWidget(self.tabs, 1)

    def load(self, inst, tab="general"):
        self.inst = inst
        d = inst.data
        self.ver.setText(f"{inst.name} · Minecraft {d['mc_version']}" +
                         (f" · {inst.loader_label} {d['loader_version']}" if d["loader"] != "vanilla" else ""))
        self.name.setText(inst.name)
        self.java.setText(d["java_path"])
        self.jvm.setText(d["jvm_args"])
        self.mods.load(inst)
        self.tabs.setCurrentIndex(1 if tab == "mods" else 0)

    def preset(self, k):
        if not self.inst:
            return
        try:
            covers.set_preset(self.inst, k)
        except OSError as e:
            self.ctl.toast(str(e), "error")
            return
        self.ctl.refresh_cards()
        self.ctl.toast(f"Обложка «{covers.PRESETS[k][0]}» применена")

    def browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "Выберите java / javaw")
        if p:
            self.java.setText(p)

    def save(self):
        if not self.inst:
            return
        fresh = self.ctl.get(self.inst.id) or self.inst  # свежие данные: время игры могло измениться
        d = fresh.data
        d["name"] = self.name.text().strip() or d["name"]
        d["java_path"] = self.java.text().strip()
        d["jvm_args"] = self.jvm.text().strip()
        fresh.save()
        self.inst = fresh
        self.ctl.refresh_all()
        self.ctl.toast("Настройки сборки сохранены")
        self.ctl.go("library")
