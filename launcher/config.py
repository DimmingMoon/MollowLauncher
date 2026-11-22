import hashlib
import json
import re
import uuid

from . import paths

DEFAULTS = {
    "accounts": [],
    "selected": "",
    "java_path": "",
    "min_mem": 512,
    "max_mem": 2048,
    "jvm_args": "",
    "width": 854,
    "height": 480,
    "theme": "emerald",
    "launcher_time": 0,
    "accent": "",            # свой цвет кнопок (#rrggbb); пусто — цвет темы
    "background": "none",    # none | scene:N | custom
    "bg_dim": 72,            # затемнение фона, %
    "game_logo": True,       # значок MollowLauncher в главном меню игры
}

NAME_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")


def offline_uuid(name):
    """Тот же UUID, что считает сам Minecraft для офлайн-игроков."""
    h = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode("utf-8")).digest())
    h[6] = (h[6] & 0x0F) | 0x30
    h[8] = (h[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(h)))


class Config:
    def __init__(self):
        self.data = dict(DEFAULTS)
        try:
            self.data.update(json.loads(paths.CONFIG.read_text("utf-8")))
        except Exception:
            pass

    def __getitem__(self, k):
        return self.data[k]

    def __setitem__(self, k, v):
        self.data[k] = v

    def save(self):
        paths.DATA.mkdir(parents=True, exist_ok=True)
        paths.CONFIG.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), "utf-8")

    def add_account(self, name):
        if any(a["name"].lower() == name.lower() for a in self.data["accounts"]):
            return
        self.data["accounts"].append({"name": name, "uuid": offline_uuid(name)})
        if not self.data["selected"]:
            self.data["selected"] = name
        self.save()

    def remove_account(self, name):
        self.data["accounts"] = [a for a in self.data["accounts"] if a["name"] != name]
        if self.data["selected"] == name:
            self.data["selected"] = self.data["accounts"][0]["name"] if self.data["accounts"] else ""
        self.save()

    def selected_account(self):
        for a in self.data["accounts"]:
            if a["name"] == self.data["selected"]:
                return a
        return None
