import json
import re
import shutil
from pathlib import Path

from . import loaders, paths

DEFAULTS = {
    "name": "",
    "mc_version": "",
    "loader": "vanilla",
    "loader_version": "",
    "java_path": "",
    "min_mem": 0,
    "max_mem": 0,
    "jvm_args": "",
    "width": 0,
    "height": 0,
    "favorite": False,
    "last_played": 0,
    "play_time": 0,
}


class Instance:
    def __init__(self, path):
        self.path = Path(path)
        self.data = dict(DEFAULTS)
        self.data.update(json.loads((self.path / "instance.json").read_text("utf-8")))

    @property
    def id(self):
        return self.path.name

    @property
    def name(self):
        return self.data["name"]

    @property
    def game_dir(self):
        return self.path / "minecraft"

    @property
    def mods_dir(self):
        return self.game_dir / "mods"

    @property
    def version_id(self):
        d = self.data
        return loaders.get(d["loader"]).version_id(d["mc_version"], d["loader_version"])

    @property
    def cover_path(self):
        return self.path / "cover.png"

    @property
    def mod_count(self):
        try:
            return sum(1 for f in self.mods_dir.iterdir() if f.name.endswith(".jar"))
        except OSError:
            return 0

    @property
    def loader_label(self):
        return loaders.get(self.data["loader"]).label

    def save(self):
        (self.path / "instance.json").write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), "utf-8")

    @staticmethod
    def _unique_dir(name):
        slug = re.sub(r"[^\w\-. ]", "_", name).strip() or "instance"
        p = paths.INSTANCES / slug
        i = 2
        while p.exists():
            p = paths.INSTANCES / f"{slug}_{i}"
            i += 1
        return p

    @classmethod
    def create(cls, name, mc, loader="vanilla", loader_version=""):
        p = cls._unique_dir(name)
        (p / "minecraft" / "mods").mkdir(parents=True)
        d = dict(DEFAULTS, name=name, mc_version=mc, loader=loader, loader_version=loader_version)
        (p / "instance.json").write_text(json.dumps(d, indent=2, ensure_ascii=False), "utf-8")
        return cls(p)

    @classmethod
    def all(cls):
        out = []
        if paths.INSTANCES.exists():
            for d in sorted(paths.INSTANCES.iterdir(), key=lambda x: x.name.lower()):
                if (d / "instance.json").exists():
                    try:
                        out.append(cls(d))
                    except Exception:
                        pass
        return out

    def clone(self):
        new = self._unique_dir(self.name + " (копия)")
        shutil.copytree(self.path, new)
        c = Instance(new)
        c.data["name"] = self.name + " (копия)"
        c.save()
        return c

    def delete(self):
        shutil.rmtree(self.path, ignore_errors=True)
