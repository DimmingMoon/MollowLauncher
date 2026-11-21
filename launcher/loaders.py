"""Реестр загрузчиков. Чтобы добавить Forge/NeoForge, достаточно написать класс
Loader и вызвать register(...) — UI подхватит его автоматически."""
from . import fabric, paths


class Loader:
    id = "vanilla"
    label = "Vanilla"

    def versions(self, mc):
        return []

    def version_id(self, mc, loader_version):
        return mc

    def ensure_profile(self, mc, loader_version):
        """Гарантирует наличие профиля версии на диске."""


class Fabric(Loader):
    id = "fabric"
    label = "Fabric"

    def versions(self, mc):
        return fabric.loader_versions(mc)

    def version_id(self, mc, loader_version):
        return f"fabric-loader-{loader_version}-{mc}"

    def ensure_profile(self, mc, loader_version):
        vid = self.version_id(mc, loader_version)
        if not (paths.VERSIONS / vid / f"{vid}.json").exists():
            fabric.install_profile(mc, loader_version)


REGISTRY = {}


def register(loader):
    REGISTRY[loader.id] = loader


def get(loader_id):
    return REGISTRY.get(loader_id, REGISTRY["vanilla"])


def all_loaders():
    return list(REGISTRY.values())


register(Loader())
register(Fabric())
