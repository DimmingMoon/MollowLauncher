"""Скины и плащи офлайн-аккаунтов.
Файлы хранятся в <данные>/skins/<ник в нижнем регистре>/{skin,cape}.png. В игру они попадают через мод
CustomSkinLoader (его лаунчер ставит сам из Modrinth): файлы кладутся в CustomSkinLoader/LocalSkin/."""
import base64
import json
import shutil
import struct

from . import modrinth, net, paths

CSL_SLUG = "customskinloader"


def _dir(name):
    return paths.SKINS / name.lower()


def skin_path(name):
    return _dir(name) / "skin.png"


def cape_path(name):
    return _dir(name) / "cape.png"


def has_skin(name):
    return skin_path(name).exists()


def has_cape(name):
    return cape_path(name).exists()


def png_size(data):
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Это не PNG-файл")
    return struct.unpack(">II", data[16:24])


def check_skin(data):
    w, h = png_size(data)
    if not (64 <= w <= 1024 and (h == w or h * 2 == w)):
        raise ValueError(f"Скин должен быть PNG 64×64 или 64×32 (у файла {w}×{h})")


def check_cape(data):
    w, h = png_size(data)
    ok = w >= 22 and h >= 17 and (w == h * 2 or w * 17 == h * 22)
    if not ok or w > 1024:
        raise ValueError(f"Плащ должен быть PNG 64×32 или 22×17 (у файла {w}×{h})")


def _put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def set_skin(name, data):
    check_skin(data)
    _put(skin_path(name), data)


def set_cape(name, data):
    check_cape(data)
    _put(cape_path(name), data)


def clear_skin(name):
    skin_path(name).unlink(missing_ok=True)


def clear_cape(name):
    cape_path(name).unlink(missing_ok=True)


def fetch_by_nick(nick):
    """Скачивает скин и плащ лицензионного игрока с серверов Mojang. Возвращает (skin|None, cape|None)."""
    r = net.S.get(f"https://api.mojang.com/users/profiles/minecraft/{nick}", timeout=15)
    if r.status_code in (204, 404):
        raise LookupError(f"Игрок «{nick}» не найден")
    r.raise_for_status()
    uid = r.json()["id"]
    prof = net.get_json(f"https://sessionserver.mojang.com/session/minecraft/profile/{uid}")
    tex = {}
    for prop in prof.get("properties", []):
        if prop.get("name") == "textures":
            tex = json.loads(base64.b64decode(prop["value"])).get("textures", {})

    def get(kind):
        url = tex.get(kind, {}).get("url")
        if not url:
            return None
        rr = net.S.get(url.replace("http://", "https://"), timeout=20)
        rr.raise_for_status()
        return rr.content

    return get("SKIN"), get("CAPE")


def fetch_part(nick, kind):
    """Скачивает только скин (kind="skin") или только плащ (kind="cape") лицензионного игрока."""
    skin, cape = fetch_by_nick(nick)
    return skin if kind == "skin" else cape


# ---- доставка в игру
def has_csl(inst):
    try:
        return any(f.name.lower().endswith(".jar") and "customskinloader" in f.name.lower()
                   for f in inst.mods_dir.iterdir())
    except OSError:
        return False


def _sync_one(src, dst):
    mark = dst.with_name(dst.name + ".mollow")  # метка «файл положил лаунчер»
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        mark.write_bytes(b"")
    elif mark.exists():  # скин убрали в лаунчере — убираем и нашу копию (чужие файлы не трогаем)
        dst.unlink(missing_ok=True)
        mark.unlink(missing_ok=True)


_LOCAL_ENTRY = {
    "name": "LocalSkin", "type": "Legacy", "checkPNG": False,
    "skin": "LocalSkin/skins/{USERNAME}.png", "model": "auto",
    "cape": "LocalSkin/capes/{USERNAME}.png", "elytra": "LocalSkin/elytras/{USERNAME}.png",
}


def _is_local(entry):
    return isinstance(entry, dict) and (entry.get("name") == "LocalSkin" or "LocalSkin" in str(entry.get("skin", "")))


def ensure_config(game_dir):
    """Ставит локальные файлы ПЕРВЫМИ в списке источников CustomSkinLoader.
    Иначе, если ник совпадает с настоящим аккаунтом Mojang, мод берёт скин оттуда (а плащ, которого там нет,
    добирает из локальных файлов) — поэтому плащ был виден, а скин нет."""
    cfg_dir = game_dir / "CustomSkinLoader"
    cfg = cfg_dir / "CustomSkinLoader.json"
    data = None
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text("utf-8-sig"))
        except (OSError, ValueError):
            return  # непонятный файл — не трогаем
        if not isinstance(data, dict):
            return
    if data is None:
        data = {"enable": True, "loadlist": [dict(_LOCAL_ENTRY), {"name": "Mojang", "type": "MojangAPI"}]}
    lst = data.get("loadlist")
    if not isinstance(lst, list):
        lst = []
    loc = [e for e in lst if _is_local(e)]
    rest = [e for e in lst if not _is_local(e)]
    new = (loc[:1] or [dict(_LOCAL_ENTRY)]) + rest
    data["loadlist"] = new
    data["enableLocalProfileCache"] = False  # без кэша профилей — смена скина видна сразу
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")


def _drop_profile_cache(game_dir, name):
    cache = game_dir / "CustomSkinLoader" / "ProfileCache"
    try:
        for f in cache.iterdir():
            if f.stem.lower() == name.lower():
                f.unlink(missing_ok=True)
    except OSError:
        pass


def sync_files(game_dir, name):
    base = game_dir / "CustomSkinLoader" / "LocalSkin"
    _sync_one(skin_path(name), base / "skins" / f"{name}.png")
    _sync_one(cape_path(name), base / "capes" / f"{name}.png")
    ensure_config(game_dir)
    _drop_profile_cache(game_dir, name)


def apply(inst, name):
    """Готовит сборку к показу скина/плаща. Возвращает список пояснений для лога (пустой — всё хорошо)."""
    notes = []
    loader = inst.data["loader"]
    if not modrinth.supported(loader):
        return ["Скин и плащ видны только в сборках с загрузчиком (Fabric): в чистом Vanilla офлайн-скины не работают."]
    if not has_csl(inst):
        try:
            modrinth.install(inst, CSL_SLUG, "CustomSkinLoader")
        except net.Cancelled:
            raise
        except LookupError:
            return [f"CustomSkinLoader пока недоступен для Minecraft {inst.data['mc_version']} — скин и плащ не применены."]
        except Exception as e:  # noqa
            return [f"Не удалось установить CustomSkinLoader: {e}"]
    sync_files(inst.game_dir, name)
    return notes
