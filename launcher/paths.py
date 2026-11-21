import os
import shutil
import sys
from pathlib import Path

APP_NAME = "MollowLauncher"

if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).parent
else:
    BASE = Path(__file__).resolve().parent.parent


def resource(rel):
    """Путь к ресурсу программы (работает и из исходников, и из PyInstaller-сборки)."""
    return Path(getattr(sys, "_MEIPASS", BASE)) / rel


def _default_data():
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(root) / ".MollowLauncher"          # C:\Users\<имя>\AppData\Roaming\.MollowLauncher
    return Path.home() / ".MollowLauncher"


_CUSTOM = os.environ.get("MOLLOW_HOME") or os.environ.get("MMCLITE_HOME")
DATA = Path(_CUSTOM) if _CUSTOM else _default_data()
LEGACY = BASE / "data"  # так хранила данные старая версия MMCLite
INSTANCES = DATA / "instances"
LIBRARIES = DATA / "libraries"
ASSETS = DATA / "assets"
VERSIONS = DATA / "versions"
JAVA = DATA / "java"
CACHE = DATA / "cache"
CONFIG = DATA / "config.json"


def migrate_legacy():
    """Переносит данные старой версии (папка data рядом с программой) в новую папку данных.
    Возвращает True, если что-то было перенесено."""
    if _CUSTOM or not LEGACY.is_dir():
        return False
    try:
        if LEGACY.resolve() == DATA.resolve():
            return False
    except OSError:
        return False
    if INSTANCES.is_dir() and any(INSTANCES.iterdir()):
        return False  # в новом месте уже есть сборки — ничего не трогаем
    DATA.mkdir(parents=True, exist_ok=True)
    moved = False
    for child in list(LEGACY.iterdir()):
        target = DATA / child.name
        if target.exists():
            if target.is_dir() and not any(target.iterdir()):
                target.rmdir()
            else:
                continue
        try:
            shutil.move(str(child), str(target))
            moved = True
        except OSError:
            pass
    try:
        LEGACY.rmdir()
    except OSError:
        pass
    return moved


def ensure():
    migrated = migrate_legacy()
    for p in (DATA, INSTANCES, LIBRARIES, ASSETS, VERSIONS, JAVA, CACHE):
        p.mkdir(parents=True, exist_ok=True)
    return migrated
