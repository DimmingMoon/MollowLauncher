import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import requests

from . import net, paths

EXE = "java.exe" if os.name == "nt" else "java"
_cache = {}


def probe(path):
    path = str(path)
    if path in _cache:
        return _cache[path]
    major = None
    try:
        kw = {"creationflags": 0x08000000} if os.name == "nt" else {}
        r = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=15,
                           stdin=subprocess.DEVNULL, **kw)
        m = re.search(r'version "(\d+)(?:\.(\d+))?', r.stderr + r.stdout)
        if m:
            major = int(m.group(1))
            if major == 1:
                major = int(m.group(2) or 8)
    except Exception:
        pass
    _cache[path] = major
    return major


def candidates():
    c = []
    jh = os.environ.get("JAVA_HOME")
    if jh:
        c.append(Path(jh) / "bin" / EXE)
    w = shutil.which("java")
    if w:
        c.append(Path(w))
    roots = [paths.JAVA]
    if os.name == "nt":
        for env in ("ProgramFiles", "ProgramFiles(x86)"):
            b = os.environ.get(env)
            if b:
                for sub in ("Java", "Eclipse Adoptium", "Microsoft", "Zulu", "BellSoft",
                            "Amazon Corretto", "AdoptOpenJDK", "Semeru"):
                    roots.append(Path(b) / sub)
        ap = os.environ.get("APPDATA")
        if ap:
            roots.append(Path(ap) / ".minecraft" / "runtime")
    else:
        roots += [Path("/usr/lib/jvm"), Path.home() / ".sdkman/candidates/java"]
    for r in roots:
        if r.is_dir():
            c += list(r.glob("**/bin/" + EXE))
    return c


def find_all():
    seen, out = set(), []
    for p in candidates():
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        if key in seen or not p.exists():
            continue
        seen.add(key)
        m = probe(p)
        if m:
            out.append((str(p), m))
    return sorted(out, key=lambda x: x[1])


def pick(major):
    infos = find_all()
    for p, m in infos:
        if m == major:
            return p
    if major > 8:
        for p, m in infos:
            if m > major:
                return p
    return None


def download_java(major, progress):
    osn = "windows" if os.name == "nt" else ("mac" if sys.platform == "darwin" else "linux")
    mach = platform.machine().lower()
    arch = "aarch64" if mach in ("arm64", "aarch64") else "x64"
    url = f"https://api.adoptium.net/v3/binary/latest/{major}/ga/{osn}/{arch}/jdk/hotspot/normal/eclipse"
    paths.JAVA.mkdir(parents=True, exist_ok=True)
    arc = paths.JAVA / f"jdk-{major}.download"
    with requests.get(url, stream=True, timeout=60, allow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        net.begin_stage(total or None)
        done = 0
        with open(arc, "wb") as f:
            for ch in r.iter_content(1 << 17):
                if net.CANCEL.is_set():
                    f.close()
                    arc.unlink(missing_ok=True)
                    raise net.Cancelled()
                f.write(ch)
                net.add_bytes(len(ch))
                done += len(ch)
                progress(f"Скачивание Java {major}", done, total or done)
    dest = paths.JAVA / f"jdk-{major}"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir()
    progress(f"Распаковка Java {major}", 0, 1)
    if zipfile.is_zipfile(arc):
        with zipfile.ZipFile(arc) as z:
            z.extractall(dest)
    else:
        with tarfile.open(arc) as t:
            t.extractall(dest)
    arc.unlink()
    _cache.clear()
    for p in dest.glob("**/bin/" + EXE):
        return str(p)
    raise RuntimeError("В архиве не найдена Java")
