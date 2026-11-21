"""Download management: скачивание файлов, реальная статистика и безопасная отмена."""
import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

S = requests.Session()
S.headers["User-Agent"] = "MollowLauncher/2.0 (github.com/mollow/launcher)"


class Cancelled(Exception):
    pass


CANCEL = threading.Event()
_lock = threading.Lock()
# bytes — всего скачано за операцию; stage_* — текущий этап.
# stage_total = None, если размер этапа заранее неизвестен.
STATS = {"bytes": 0, "stage_bytes": 0, "stage_total": None}


def reset_stats():
    CANCEL.clear()
    with _lock:
        STATS.update(bytes=0, stage_bytes=0, stage_total=None)


def begin_stage(total):
    with _lock:
        STATS["stage_bytes"] = 0
        STATS["stage_total"] = total


def add_bytes(n):
    with _lock:
        STATS["bytes"] += n
        STATS["stage_bytes"] += n


def get_json(url, params=None):
    r = S.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ok(dest, sha1, size):
    if not dest.exists():
        return False
    if size is not None:
        return dest.stat().st_size == size
    if sha1:
        return sha1_of(dest) == sha1
    return True


def download(url, dest, sha1=None, size=None, retries=3):
    dest = Path(dest)
    if CANCEL.is_set():
        raise Cancelled()
    if _ok(dest, sha1, size):
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    for i in range(retries):
        got = 0
        try:
            with S.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        if CANCEL.is_set():
                            raise Cancelled()
                        f.write(chunk)
                        got += len(chunk)
                        add_bytes(len(chunk))
            if sha1 and sha1_of(tmp) != sha1:
                raise IOError("sha1 mismatch: " + url)
            tmp.replace(dest)
            return True
        except Cancelled:
            tmp.unlink(missing_ok=True)
            raise
        except Exception:
            with _lock:  # откатываем счётчики неудачной попытки
                STATS["bytes"] -= got
                STATS["stage_bytes"] -= got
            if i == retries - 1:
                raise
            time.sleep(1)


def download_many(tasks, cb=None, workers=16):
    """tasks: list of (url, dest, sha1, size). cb(done, total) — по файлам."""
    total = len(tasks)
    pending = [t for t in tasks if not _ok(Path(t[1]), t[2], t[3])]
    sizes = [t[3] for t in pending]
    begin_stage(sum(sizes) if all(s is not None for s in sizes) else None)
    done = total - len(pending)
    if cb:
        cb(done, total)
    ex = ThreadPoolExecutor(workers)
    try:
        futs = [ex.submit(download, *t) for t in pending]
        for f in as_completed(futs):
            f.result()
            done += 1
            if cb and (done % 20 == 0 or done == total):
                cb(done, total)
    except BaseException:
        ex.shutdown(wait=False, cancel_futures=True)
        raise
    ex.shutdown(wait=True)
