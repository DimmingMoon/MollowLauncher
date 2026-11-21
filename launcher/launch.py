import re

from . import loaders, mojang, paths
from . import java as javamod


class JavaMissing(Exception):
    def __init__(self, major):
        super().__init__(f"Нужна Java {major}")
        self.major = major


class Spec:
    def __init__(self, java, args, cwd):
        self.java, self.args, self.cwd = java, args, cwd


def _eff(inst, cfg, key):
    """Java и JVM-аргументы можно переопределить для сборки; память и размер окна — только глобально."""
    if key in ("java_path",):
        return inst.data.get(key) or cfg[key]
    return cfg[key]


def prepare(inst, cfg, progress):
    acc = cfg.selected_account()
    if not acc:
        raise RuntimeError("Не выбран аккаунт")
    vid = inst.version_id
    d = inst.data
    loader = loaders.get(d["loader"])
    if d["loader"] != "vanilla":
        progress(loader.label, 0, 1)
        loader.ensure_profile(d["mc_version"], d["loader_version"])
    vj = mojang.install(vid, progress)

    major = vj.get("javaVersion", {}).get("majorVersion", 8)
    jp = _eff(inst, cfg, "java_path") or javamod.pick(major)
    if not jp:
        raise JavaMissing(major)

    inst.game_dir.mkdir(parents=True, exist_ok=True)
    assets_root, game_assets = mojang.prepare_assets(vj, inst.game_dir)

    cp_libs, _ = mojang.resolve_libraries(vj)
    sep = ";" if mojang.os_name() == "windows" else ":"
    cp = [str(paths.LIBRARIES / l["path"]) for l in cp_libs]
    jar = paths.VERSIONS / vj["_root"] / f"{vj['_root']}.jar"
    cp.append(str(jar))
    classpath = sep.join(cp)
    natives = str(paths.VERSIONS / vid / "natives")
    w, h = _eff(inst, cfg, "width"), _eff(inst, cfg, "height")

    ctx = {
        "auth_player_name": acc["name"],
        "version_name": vid,
        "game_directory": str(inst.game_dir),
        "assets_root": assets_root,
        "assets_index_name": vj["assetIndex"]["id"],
        "game_assets": game_assets,
        "auth_uuid": acc["uuid"].replace("-", ""),
        "auth_access_token": "0",
        "auth_session": "token:0:" + acc["uuid"].replace("-", ""),
        "clientid": "",
        "auth_xuid": "",
        "user_type": "legacy",
        "user_properties": "{}",
        "version_type": vj.get("type", "release"),
        "resolution_width": w,
        "resolution_height": h,
        "launcher_name": "MollowLauncher",
        "launcher_version": "1.0",
        "natives_directory": natives,
        "classpath": classpath,
        "classpath_separator": sep,
        "library_directory": str(paths.LIBRARIES),
        "primary_jar": str(jar),
    }

    def sub(s):
        return re.sub(r"\$\{(\w+)\}", lambda m: str(ctx.get(m.group(1), m.group(0))), s)

    feats = {"has_custom_resolution": True}

    def flat(lst):
        out = []
        for a in lst:
            if isinstance(a, str):
                out.append(sub(a))
            elif mojang.rule_ok(a.get("rules"), feats):
                v = a["value"]
                out += [sub(x) for x in ([v] if isinstance(v, str) else v)]
        return out

    if "arguments" in vj:
        jvm = flat(vj["arguments"].get("jvm", []))
        game = flat(vj["arguments"].get("game", []))
    else:
        jvm = ["-Djava.library.path=" + natives, "-cp", classpath]
        game = [sub(x) for x in vj["minecraftArguments"].split()]
        game += ["--width", str(w), "--height", str(h)]

    args = [f"-Xms{_eff(inst, cfg, 'min_mem')}M", f"-Xmx{_eff(inst, cfg, 'max_mem')}M"]
    args += (cfg["jvm_args"] + " " + d.get("jvm_args", "")).split()
    args += jvm + [vj["mainClass"]] + game
    return Spec(jp, args, str(inst.game_dir))
