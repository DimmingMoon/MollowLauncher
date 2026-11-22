from pathlib import Path

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from ... import skins
from ...config import NAME_RE
from ..skinview import SkinPreview
from ..widgets import Btn, card_frame, label, scrolled


class SkinsPage(QWidget):
    """Скин и плащ выбранного аккаунта (страница внутри лаунчера)."""

    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.name = ""
        self.title = label("Скин и плащ", "h1")
        self.sub = label("", "muted", wrap=True)
        self.preview = SkinPreview()

        back = Btn("К аккаунтам", "back", "ghost")
        back.clicked.connect(lambda: ctl.go("accounts"))
        top = QHBoxLayout()
        top.addWidget(back)
        top.addWidget(self.title)
        top.addStretch()

        up_skin = Btn("Загрузить скин…", "image", "primary")
        up_skin.clicked.connect(self.pick_skin)
        rm_skin = Btn("Убрать скин", "trash")
        rm_skin.clicked.connect(self.clear_skin)
        up_cape = Btn("Загрузить плащ…", "image")
        up_cape.clicked.connect(self.pick_cape)
        rm_cape = Btn("Убрать плащ", "trash")
        rm_cape.clicked.connect(self.clear_cape)
        self.skin_nick = QLineEdit()
        self.skin_nick.setPlaceholderText("Ник игрока, чей скин взять, например Notch")
        self.skin_nick.setMaxLength(16)
        self.skin_nick.returnPressed.connect(lambda: self.fetch("skin"))
        fetch_skin = Btn("Скачать скин", "download")
        fetch_skin.clicked.connect(lambda: self.fetch("skin"))
        self.cape_nick = QLineEdit()
        self.cape_nick.setPlaceholderText("Ник игрока, чей плащ взять, например Notch")
        self.cape_nick.setMaxLength(16)
        self.cape_nick.returnPressed.connect(lambda: self.fetch("cape"))
        fetch_cape = Btn("Скачать плащ", "download")
        fetch_cape.clicked.connect(lambda: self.fetch("cape"))

        f, l = card_frame(spacing=12)
        l.addWidget(label("Скин", "h2"))
        r1 = QHBoxLayout()
        r1.addWidget(up_skin)
        r1.addWidget(rm_skin)
        r1.addStretch()
        l.addLayout(r1)
        l.addWidget(label("Или возьмите скин существующего игрока по его нику:", "muted", wrap=True))
        r2 = QHBoxLayout()
        r2.addWidget(self.skin_nick, 1)
        r2.addWidget(fetch_skin)
        l.addLayout(r2)
        l.addSpacing(6)
        l.addWidget(label("Плащ", "h2"))
        r3 = QHBoxLayout()
        r3.addWidget(up_cape)
        r3.addWidget(rm_cape)
        r3.addStretch()
        l.addLayout(r3)
        l.addWidget(label("Или возьмите плащ существующего игрока по его нику:", "muted", wrap=True))
        r4 = QHBoxLayout()
        r4.addWidget(self.cape_nick, 1)
        r4.addWidget(fetch_cape)
        l.addLayout(r4)
        l.addSpacing(6)
        l.addWidget(label(
            "Скин — PNG 64×64 или 64×32, плащ — PNG 64×32. В игре они показываются через мод CustomSkinLoader: "
            "лаунчер сам установит его в сборку с Fabric при запуске. В сборках Vanilla офлайн-скины не работают. "
            "Скин и плащ видны только вам: на серверах остальные игроки их не увидят.", "muted", wrap=True))
        l.addStretch()

        mid = QHBoxLayout()
        mid.setSpacing(16)
        left = QVBoxLayout()
        left.addWidget(self.preview)
        left.addStretch()
        mid.addLayout(left)
        mid.addWidget(f, 1)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 8, 0)
        bl.addLayout(mid)
        bl.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 20, 20)
        root.setSpacing(10)
        root.addLayout(top)
        root.addWidget(self.sub)
        root.addWidget(scrolled(body), 1)

    def load(self, name):
        self.name = name
        self.skin_nick.clear()
        self.cape_nick.clear()

    def refresh(self):
        name = self.name
        self.sub.setText(f"Аккаунт: {name}" if name else "")
        skin = cape = None
        if name:
            if skins.has_skin(name):
                img = QImage(str(skins.skin_path(name)))
                skin = None if img.isNull() else img
            if skins.has_cape(name):
                img = QImage(str(skins.cape_path(name)))
                cape = None if img.isNull() else img
        self.preview.set_images(skin, cape)

    def _changed(self, msg):
        self.refresh()
        self.ctl.refresh_all()
        self.ctl.toast(msg)

    def _pick(self, title):
        f, _ = QFileDialog.getOpenFileName(self, title, "", "PNG (*.png)")
        return Path(f).read_bytes() if f else None

    def pick_skin(self):
        self._save(self._pick("Выберите скин (PNG)"), skins.set_skin, "Скин обновлён")

    def pick_cape(self):
        self._save(self._pick("Выберите плащ (PNG)"), skins.set_cape, "Плащ обновлён")

    def _save(self, data, setter, msg):
        if data is None or not self.name:
            return
        try:
            setter(self.name, data)
        except (ValueError, OSError) as e:
            self.ctl.toast(str(e), "error")
            return
        self._changed(msg)

    def clear_skin(self):
        if self.name:
            skins.clear_skin(self.name)
            self._changed("Скин убран")

    def clear_cape(self):
        if self.name:
            skins.clear_cape(self.name)
            self._changed("Плащ убран")

    def fetch(self, kind):
        """Скачивает с серверов Mojang только скин (kind="skin") или только плащ (kind="cape")."""
        field = self.skin_nick if kind == "skin" else self.cape_nick
        what = "скин" if kind == "skin" else "плащ"
        setter = skins.set_skin if kind == "skin" else skins.set_cape
        nick = field.text().strip() or self.name
        name = self.name
        if not name:
            return
        if not NAME_RE.match(nick):
            self.ctl.toast("Ник: латиница, цифры и _, 3–16 символов", "error")
            return
        self.ctl.toast(f"Загружаю {what} игрока {nick}…")

        def ok(data):
            if not data:
                self.ctl.toast(f"У игрока {nick} нет {'скина' if kind == 'skin' else 'плаща'}", "error")
                return
            try:
                setter(name, data)
            except (ValueError, OSError) as e:
                self.ctl.toast(str(e), "error")
                return
            self._changed(f"{what.capitalize()} загружен" if kind == "skin" else "Плащ загружен")

        def fail(e):
            self.ctl.toast(str(e) if isinstance(e, LookupError) else f"Не удалось получить {what}: {e}", "error")

        self.ctl.run(lambda cb: skins.fetch_part(nick, kind), ok, fail)
