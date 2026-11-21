"""Бизнес-логика библиотеки: поиск, фильтрация, сортировка сборок."""
import re


def mc_key(version):
    nums = [int(x) for x in re.findall(r"\d+", version)[:3]]
    return tuple(nums + [0] * (3 - len(nums)))


SORTS = [("name", "По названию"), ("recent", "Недавно запущенные"),
         ("version", "По версии Minecraft"), ("mods", "По числу модов")]


def filter_sort(insts, query="", flt="all", sort="name"):
    q = query.strip().lower()
    out = []
    for i in insts:
        d = i.data
        if flt == "favorites" and not d.get("favorite"):
            continue
        if flt not in ("all", "favorites") and d["loader"] != flt:
            continue
        if q and q not in (i.name + " " + d["mc_version"] + " " + i.loader_label).lower():
            continue
        out.append(i)
    if sort == "recent":
        out.sort(key=lambda i: i.data.get("last_played", 0), reverse=True)
    elif sort == "version":
        out.sort(key=lambda i: mc_key(i.data["mc_version"]), reverse=True)
    elif sort == "mods":
        out.sort(key=lambda i: i.mod_count, reverse=True)
    else:
        out.sort(key=lambda i: i.name.lower())
    return out
