import json
import platform
import shutil
import sys
import zipfile

from . import net, paths

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
LIB_REPO = "https://libraries.minecraft.net/"


def os_name():
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "osx"
    return "linux"


def arch_name():
    m = platform.machine().lower()
    if m in ("x86", "i386", "i686"):
        return "x86"
    if m in ("arm64", "aarch64"):
        return "arm64"
    return "x86_64"


def rule_ok(rules, features=None):
    if not rules:
        return True
    features = features or {}
    allowed = False
    for r in rules:
        match = True
        o = r.get("os")
        if o:
            if "name" in o and o["name"] != os_name():
                match = False
            if "arch" in o and o["arch"] != arch_name():
                match = False
        for k, v in r.get("features", {}).items():
            if bool(features.get(k, False)) != v:
                match = False
        if match:
            allowed = r.get("action") == "allow"
    return allowed


def manifest():
    p = paths.DATA / "version_manifest.json"
    try:
        d = net.get_json(MANIFEST)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d), "utf-8")
        return d
    except Exception:
        if p.exists():
            return json.loads(p.read_text("utf-8"))
        raise


def version_json(vid):
    p = paths.VERSIONS / vid / f"{vid}.json"
    if p.exists():
        return json.loads(p.read_text("utf-8"))
    for v in manifest()["versions"]:
        if v["id"] == vid:
            data = net.get_json(v["url"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data), "utf-8")
            return data
    raise ValueError(f"Версия {vid} не найдена")


def merge(p, c):
    r = dict(p)
    for k, v in c.items():
        if k in ("libraries", "inheritsFrom"):
            continue
        if k == "arguments":
            pa = p.get("arguments", {})
            r["arguments"] = {
                "game": list(pa.get("game", [])) + list(v.get("game", [])),
                "jvm": list(pa.get("jvm", [])) + list(v.get("jvm", [])),
            }
        else:
            r[k] = v
    r["libraries"] = list(c.get("libraries", [])) + list(p.get("libraries", []))
    return r


def load_merged(vid):
    j = version_json(vid)
    if "inheritsFrom" in j:
        return merge(load_merged(j["inheritsFrom"]), j)
    j = dict(j)
    j["_root"] = j["id"]
    return j


def _maven_path(name):
    parts = name.split(":")
    g, a, v = parts[0], parts[1], parts[2]
    cl = "-" + parts[3] if len(parts) > 3 else ""
    return f"{g.replace('.', '/')}/{a}/{v}/{a}-{v}{cl}.jar"


def resolve_libraries(vj):
    """Возвращает (classpath_libs, natives). Элементы — dict path/url/sha1/size."""
    cp, natives, seen = [], [], set()
    for lib in vj["libraries"]:
        if not rule_ok(lib.get("rules")):
            continue
        name = lib["name"]
        parts = name.split(":")
        key = ":".join(parts[:2]) + (":" + parts[3] if len(parts) > 3 else "")
        dl = lib.get("downloads")
        if "natives" in lib:
            cls = lib["natives"].get(os_name())
            if cls:
                cls = cls.replace("${arch}", "32" if arch_name() == "x86" else "64")
                art = (dl or {}).get("classifiers", {}).get(cls)
                if art:
                    natives.append((art, lib.get("extract", {})))
        if key in seen:
            continue
        if dl and "artifact" in dl:
            art = dl["artifact"]
            if not art.get("url"):
                continue
            cp.append(art)
        elif dl and "natives" in lib:
            continue
        else:
            path = _maven_path(name)
            cp.append({"path": path, "url": lib.get("url", LIB_REPO) + path})
        seen.add(key)
    return cp, natives


def extract_natives(vid, natives):
    d = paths.VERSIONS / vid / "natives"
    if d.exists() and any(d.iterdir()):
        return
    d.mkdir(parents=True, exist_ok=True)
    for art, ex in natives:
        excl = ex.get("exclude", [])
        with zipfile.ZipFile(paths.LIBRARIES / art["path"]) as z:
            for m in z.namelist():
                if m.endswith("/") or any(m.startswith(e) for e in excl):
                    continue
                z.extract(m, d)


def install(vid, progress):
    vj = load_merged(vid)
    root = vj["_root"]
    progress("Клиент Minecraft", 0, 1)
    c = vj["downloads"]["client"]
    net.begin_stage(c.get("size"))
    net.download(c["url"], paths.VERSIONS / root / f"{root}.jar", c.get("sha1"), c.get("size"))

    cp, natives = resolve_libraries(vj)
    tasks = [(l["url"], paths.LIBRARIES / l["path"], l.get("sha1"), l.get("size")) for l in cp]
    tasks += [(a["url"], paths.LIBRARIES / a["path"], a.get("sha1"), a.get("size")) for a, _ in natives]
    net.download_many(tasks, lambda d, n: progress("Библиотеки", d, n))

    ai = vj["assetIndex"]
    idxp = paths.ASSETS / "indexes" / f"{ai['id']}.json"
    net.download(ai["url"], idxp, ai.get("sha1"), ai.get("size"))
    idx = json.loads(idxp.read_text("utf-8"))
    tasks = []
    for obj in idx["objects"].values():
        h = obj["hash"]
        tasks.append((f"https://resources.download.minecraft.net/{h[:2]}/{h}",
                      paths.ASSETS / "objects" / h[:2] / h, None, obj.get("size")))
    net.download_many(tasks, lambda d, n: progress("Ресурсы", d, n))

    extract_natives(vid, natives)
    return vj


def prepare_assets(vj, game_dir):
    """Для старых версий (до 1.7) копирует ассеты в «виртуальную» структуру."""
    idx = json.loads((paths.ASSETS / "indexes" / f"{vj['assetIndex']['id']}.json").read_text("utf-8"))
    game_assets = paths.ASSETS / "virtual" / "legacy"
    if idx.get("virtual") or idx.get("map_to_resources"):
        target = game_dir / "resources" if idx.get("map_to_resources") else game_assets
        for name, obj in idx["objects"].items():
            h = obj["hash"]
            src = paths.ASSETS / "objects" / h[:2] / h
            dst = target / name
            if src.exists() and not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        game_assets = target
    return str(paths.ASSETS), str(game_assets)
