"""Каталог модов Modrinth: поиск и установка (вместе с обязательными зависимостями) в сборку."""
import json

from . import net

API = "https://api.modrinth.com/v2"
SORTS = [("relevance", "Релевантность"), ("downloads", "Скачивания"),
         ("updated", "Обновление"), ("newest", "Новые")]
LOADERS = ("fabric", "quilt", "forge", "neoforge")  # Vanilla модов не поддерживает


def supported(loader_id):
    return loader_id in LOADERS


def search(query, mc, loader, sort="relevance", offset=0, limit=20):
    facets = [["project_type:mod"], [f"versions:{mc}"], [f"categories:{loader}"]]
    data = net.get_json(f"{API}/search", params={
        "query": query, "facets": json.dumps(facets), "index": sort, "offset": offset, "limit": limit})
    return data["hits"], data.get("total_hits", 0)


def pick_version(project_id, mc, loader):
    """Лучшая версия мода под игру и загрузчик: релиз > бета > альфа, внутри — самая новая."""
    vs = net.get_json(f"{API}/project/{project_id}/version", params={
        "loaders": json.dumps([loader]), "game_versions": json.dumps([mc])})
    if not vs:
        return None
    order = {"release": 0, "beta": 1, "alpha": 2}
    return sorted(vs, key=lambda v: order.get(v.get("version_type"), 3))[0]  # сортировка устойчива


# --- индекс установленных из Modrinth модов (чтобы показывать «Установлен» и не дублировать)
def _index_path(inst):
    return inst.path / "mods_index.json"


def read_index(inst):
    try:
        return json.loads(_index_path(inst).read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def installed_ids(inst):
    out = set()
    for pid, e in read_index(inst).items():
        f = inst.mods_dir / e["file"]
        if f.exists() or f.with_name(f.name + ".disabled").exists():
            out.add(pid)
    return out


def install(inst, project_id, title="", ctx=None):
    """Скачивает мод и обязательные зависимости в папку модов сборки.
    Возвращает ctx: {"done": [(project_id, файл)], "warn": [текст]}."""
    ctx = ctx if ctx is not None else {"seen": set(), "done": [], "warn": []}
    if project_id in ctx["seen"]:
        return ctx
    ctx["seen"].add(project_id)
    mc, loader = inst.data["mc_version"], inst.data["loader"]
    v = pick_version(project_id, mc, loader)
    if not v:
        raise LookupError(f"Нет версии для Minecraft {mc} ({loader})")
    have = installed_ids(inst)
    for dep in v.get("dependencies", []):
        pid = dep.get("project_id")
        if dep.get("dependency_type") == "required" and pid and pid not in have:
            try:
                install(inst, pid, ctx=ctx)
            except LookupError:
                ctx["warn"].append(f"Зависимость {pid} недоступна для этой версии")
    f = next((x for x in v["files"] if x.get("primary")), v["files"][0])
    inst.mods_dir.mkdir(parents=True, exist_ok=True)
    dest = inst.mods_dir / f["filename"]
    if not dest.with_name(dest.name + ".disabled").exists():  # отключённая копия уже есть — не дублируем
        net.download(f["url"], dest, f.get("hashes", {}).get("sha1"), f.get("size"))
    idx = read_index(inst)
    idx[project_id] = {"file": f["filename"], "title": title or v.get("name", ""),
                       "version": v.get("version_number", "")}
    _index_path(inst).write_text(json.dumps(idx, indent=2, ensure_ascii=False), "utf-8")
    ctx["done"].append((project_id, f["filename"]))
    return ctx
