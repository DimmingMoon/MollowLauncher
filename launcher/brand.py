"""MollowLauncher в главном меню игры: лаунчер кладёт в сборку маленький ресурспак, который заменяет
логотип «MINECRAFT» на иконку и название лаунчера (надпись «JAVA EDITION» под ним убирается),
и включает пакет в options.txt."""
import json
import re
import zipfile

from . import paths

PACK_NAME = "MollowLauncher.zip"
ENTRY = "file/" + PACK_NAME

_FORMATS = [  # (minor, patch) версии 1.x.y -> pack_format
    ((21, 11), 75), ((21, 9), 69), ((21, 7), 64), ((21, 6), 63), ((21, 5), 55), ((21, 4), 46), ((21, 2), 42),
    ((21, 0), 34), ((20, 5), 32), ((20, 3), 22), ((20, 2), 18), ((20, 0), 15), ((19, 4), 13), ((19, 3), 12),
    ((19, 0), 9), ((18, 0), 8), ((17, 0), 7), ((16, 2), 6),
]


def pack_format(mc):
    m = re.match(r"1\.(\d+)(?:\.(\d+))?", mc or "")
    if not m:
        return 75
    v = (int(m.group(1)), int(m.group(2) or 0))
    for ver, fmt in _FORMATS:
        if v >= ver:
            return fmt
    return 5


def mcmeta(mc):
    fmt = pack_format(mc)
    pack = {"pack_format": fmt, "description": "MollowLauncher"}
    if fmt >= 69:
        pack.update(min_format=fmt, max_format=999)
    elif fmt >= 18:
        pack["supported_formats"] = {"min_inclusive": 1, "max_inclusive": 999}
    return json.dumps({"pack": pack})


def set_options_entry(path, enabled):
    """Добавляет/убирает наш пакет в строке resourcePacks файла options.txt. Остальное не трогает."""
    lines = path.read_text("utf-8").splitlines() if path.exists() else []
    idx = next((i for i, l in enumerate(lines) if l.startswith("resourcePacks:")), None)
    if idx is None:
        if not enabled:
            return
        packs = ["vanilla"]
    else:
        try:
            packs = json.loads(lines[idx].split(":", 1)[1])
        except (ValueError, IndexError):
            return  # непонятный формат — лучше не трогать
    if enabled and ENTRY not in packs:
        pos = 0
        while pos < len(packs) and not str(packs[pos]).startswith("file/"):
            pos += 1  # после встроенных пакетов, но ниже пакетов игрока
        packs.insert(pos, ENTRY)
    elif not enabled and ENTRY in packs:
        packs.remove(ENTRY)
    elif idx is not None:
        return
    line = "resourcePacks:" + json.dumps(packs, separators=(",", ":"), ensure_ascii=False)
    if idx is None:
        lines.append(line)
    else:
        lines[idx] = line
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", "utf-8")


TITLE = "assets/minecraft/textures/gui/title/"


def install_pack(inst):
    edition = paths.BRAND / "edition.png"
    legacy = pack_format(inst.data["mc_version"]) < 12  # до 1.19.3 логотип — атлас из двух половинок
    logo = paths.BRAND / ("logo_legacy.png" if legacy else "logo.png")
    if not edition.exists() or not logo.exists():
        return
    rp = inst.game_dir / "resourcepacks"
    rp.mkdir(parents=True, exist_ok=True)
    icon = paths.BRAND / "pack.png"
    with zipfile.ZipFile(rp / PACK_NAME, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", mcmeta(inst.data["mc_version"]))
        if icon.exists():
            z.write(icon, "pack.png")
        z.write(logo, TITLE + "minecraft.png")
        z.write(edition, TITLE + "edition.png")  # пустая картинка: «JAVA EDITION» не показывается
    set_options_entry(inst.game_dir / "options.txt", True)


def remove_pack(inst):
    z = inst.game_dir / "resourcepacks" / PACK_NAME
    if z.exists():
        z.unlink()
    set_options_entry(inst.game_dir / "options.txt", False)
