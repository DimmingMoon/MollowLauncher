import json

from . import net, paths

META = "https://meta.fabricmc.net/v2"


def loader_versions(mc):
    data = net.get_json(f"{META}/versions/loader/{mc}")
    return [e["loader"]["version"] for e in data]


def install_profile(mc, loader):
    data = net.get_json(f"{META}/versions/loader/{mc}/{loader}/profile/json")
    vid = data["id"]
    p = paths.VERSIONS / vid / f"{vid}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data), "utf-8")
    return vid
