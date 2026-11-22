"""Бизнес-логика мод-менеджера. Отключение мода = переименование в *.jar.disabled,
файл НИКОГДА не удаляется при отключении."""
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

DISABLED = ".disabled"
_cache = {}


@dataclass
class ModInfo:
    file: Path
    enabled: bool
    name: str
    version: str
    mod_id: str
    description: str
    authors: str
    size: int
    kind: str  # Fabric / Quilt / Forge / Неизвестно
    icon: bytes = None  # PNG-иконка из самого .jar (если есть)

    @property
    def filename(self):
        return self.file.name


def _guess_version(stem):
    m = re.search(r"[-_+ ]v?(\d[\w.+-]*)$", stem)
    return m.group(1) if m else ""


def _toml(text, key):
    m = re.search(rf'^\s*{key}\s*=\s*"([^"]*)"', text, re.M)
    return m.group(1) if m else ""


def _icon_bytes(z, names, path):
    """Иконка мода из jar: путь из метаданных, иначе pack.png/icon.png/logo.png в корне."""
    if isinstance(path, dict) and path:
        path = path[max(path, key=lambda k: int(k) if str(k).isdigit() else 0)]
    cands = [path] if isinstance(path, str) and path else []
    cands += ["pack.png", "icon.png", "logo.png"]
    for c in cands:
        c = c.lstrip("/")
        if c in names:
            try:
                if z.getinfo(c).file_size <= 600_000:
                    return z.read(c)
            except Exception:
                pass
    return None


def _read_meta(jar):
    meta = {"name": "", "version": "", "id": "", "description": "", "authors": "", "kind": "Неизвестно", "icon": None}
    try:
        with zipfile.ZipFile(jar) as z:
            names = set(z.namelist())
            if "fabric.mod.json" in names:
                d = json.loads(z.read("fabric.mod.json").decode("utf-8", "replace"), strict=False)
                auth = [a if isinstance(a, str) else a.get("name", "") for a in d.get("authors", [])]
                meta.update(name=d.get("name", ""), version=str(d.get("version", "")), id=d.get("id", ""),
                            description=d.get("description", ""), authors=", ".join(filter(None, auth)),
                            kind="Fabric", icon=_icon_bytes(z, names, d.get("icon")))
            elif "quilt.mod.json" in names:
                d = json.loads(z.read("quilt.mod.json").decode("utf-8", "replace"), strict=False)
                ql = d.get("quilt_loader", {})
                md = ql.get("metadata", {})
                meta.update(name=md.get("name", ""), version=str(ql.get("version", "")), id=ql.get("id", ""),
                            description=md.get("description", ""), kind="Quilt",
                            icon=_icon_bytes(z, names, md.get("icon")))
            else:
                for tn in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
                    if tn in names:
                        t = z.read(tn).decode("utf-8", "replace")
                        meta.update(name=_toml(t, "displayName"), version=_toml(t, "version"),
                                    id=_toml(t, "modId"), authors=_toml(t, "authors"),
                                    description=(re.search(r"description\s*=\s*'''(.*?)'''", t, re.S) or
                                                 re.search(r'description\s*=\s*"([^"]*)"', t) or [None, ""])[1].strip(),
                                    kind="NeoForge" if "neoforge" in tn else "Forge",
                                    icon=_icon_bytes(z, names, _toml(t, "logoFile")))
                        break
    except Exception:
        pass
    return meta


def list_mods(inst):
    d = inst.mods_dir
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for f in sorted(d.iterdir(), key=lambda x: x.name.lower()):
        enabled = f.name.endswith(".jar")
        if not (enabled or f.name.endswith(".jar" + DISABLED)):
            continue
        st = f.stat()
        key = (str(f), st.st_mtime_ns)
        if key not in _cache:
            _cache[key] = _read_meta(f)
        m = _cache[key]
        stem = f.name.removesuffix(DISABLED).removesuffix(".jar")
        version = m["version"]
        if not version or "${" in version:
            version = _guess_version(stem)
        out.append(ModInfo(f, enabled, m["name"] or stem, version, m["id"],
                           m["description"], m["authors"], st.st_size, m["kind"], m.get("icon")))
    return out


def set_enabled(info, enabled):
    """Переименовывает файл; возвращает новый путь. Ничего не удаляет и не перезаписывает."""
    base = info.file.name.removesuffix(DISABLED)
    target = info.file.with_name(base if enabled else base + DISABLED)
    if target == info.file:
        return target
    if target.exists():
        raise FileExistsError(f"Файл {target.name} уже существует")
    info.file.rename(target)
    info.file = target
    info.enabled = enabled
    return target


def delete_mod(info):
    info.file.unlink()


def add_mods(inst, files):
    """Копирует .jar в папку модов, не перезаписывая существующие. Возвращает список имён."""
    inst.mods_dir.mkdir(parents=True, exist_ok=True)
    added = []
    for f in files:
        src = Path(f)
        if src.suffix.lower() != ".jar":
            continue
        dst = inst.mods_dir / src.name
        i = 2
        while dst.exists() or dst.with_name(dst.name + DISABLED).exists():
            dst = inst.mods_dir / f"{src.stem}_{i}{src.suffix}"
            i += 1
        shutil.copy2(src, dst)
        added.append(dst.name)
    return added
