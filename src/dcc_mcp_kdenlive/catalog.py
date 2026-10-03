"""Discover actual installed MLT services and Kdenlive asset definitions."""

import os
import re
import stat
from pathlib import Path

from defusedxml import ElementTree

from .runtime import executable, run_native
from .storage import read_xml


def query_services(kind="filters", service=""):
    singular = {
        "filters": "filter",
        "transitions": "transition",
        "producers": "producer",
        "consumers": "consumer",
    }
    if kind not in singular:
        raise ValueError("Unknown service kind")
    if service and not re.fullmatch(r"[A-Za-z0-9_.-]+", service):
        raise ValueError("Invalid service ID")
    query = singular[kind] + "=" + service if service else kind
    output = run_native([executable("melt"), "-query", query])
    return {"kind": kind, "service": service, "metadata": output, "source": "installed_mlt"}


def data_directory():
    configured = os.environ.get("DCC_MCP_KDENLIVE_DATA")
    if configured:
        return Path(configured).resolve(strict=True)
    editor = os.environ.get("DCC_MCP_KDENLIVE_EXECUTABLE")
    candidates = [Path("/usr/share/kdenlive"), Path("/usr/local/share/kdenlive")]
    if editor:
        candidates = [
            Path(editor).parent / "data/kdenlive",
            Path(editor).parent.parent / "share/kdenlive",
        ] + candidates
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Set DCC_MCP_KDENLIVE_DATA to the installed Kdenlive data directory")


def list_assets(kind="effects", query="", limit=100):
    if kind not in (
        "effects",
        "transitions",
        "titles",
        "profiles",
        "export",
        "generators",
        "lumas",
        "luts",
    ):
        raise ValueError("Unknown asset category")
    if not 1 <= limit <= 500:
        raise ValueError("Limit must be 1..500")
    base = data_directory()
    paths = sorted(
        path.relative_to(base).as_posix()
        for path in (base / kind).rglob("*")
        if path.is_file() and query.lower() in path.name.lower()
    )
    return {"assets": paths[:limit], "total": len(paths), "truncated": len(paths) > limit}


def describe_asset(asset):
    base = data_directory().resolve()
    path = (base / asset).resolve(strict=True)
    if base not in path.parents:
        raise ValueError("Asset must be inside the installed data directory")
    _, _, root = read_xml(path)
    return {
        "asset": asset,
        "attributes": dict(root.attrib),
        "parameters": [
            dict(node.attrib) for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "parameter"
        ],
    }


def validate_effect_identity(effect_id, service):
    """Resolve an installed XML effect definition before emitting native identity.

    This intentionally requires an installed XML definition; custom effects
    known only to an editor's in-memory repository are not assumed available.
    """
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", effect_id):
        raise ValueError("Invalid native effect identifier")
    effects = data_directory() / "effects"
    if effects.is_symlink():
        raise ValueError("Installed effects directory must not be a symlink")
    base = effects.resolve(strict=True)
    if not base.is_dir():
        raise ValueError("Installed effects directory is unavailable")
    tags = set()
    count = 0
    total = 0
    directories = 0

    def walk_error(error):
        raise error

    for directory, subdirs, files in os.walk(str(base), followlinks=False, onerror=walk_error):
        directories += 1
        if directories > 256:
            raise ValueError("Installed effect catalog exceeds directory limit")
        subdirs[:] = sorted(name for name in subdirs if not (Path(directory) / name).is_symlink())
        for name in sorted(files):
            if not name.lower().endswith(".xml"):
                continue
            count += 1
            if count > 1024:
                raise ValueError("Installed effect catalog exceeds file limit")
            path = Path(directory) / name
            if (
                not stat.S_ISREG(path.lstat().st_mode)
                or base not in path.resolve(strict=True).parents
            ):
                raise ValueError("Installed effect definitions must be regular catalog files")
            flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(str(path), flags)
            with os.fdopen(descriptor, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError("Opened effect definition is not a regular file")
                data = stream.read(256 * 1024 + 1)
            total += len(data)
            if len(data) > 256 * 1024 or total > 16 * 1024 * 1024:
                raise ValueError("Installed effect catalog exceeds byte limit")
            root = ElementTree.fromstring(data)
            for node in root.iter():
                if node.tag not in ("effect", "{https://www.kdenlive.org}effect"):
                    continue
                if node.get("id", node.get("tag")) == effect_id:
                    tags.add(node.get("tag", ""))
    if not tags:
        raise ValueError("Native effect ID is not in the installed XML catalog")
    if tags != {service}:
        raise ValueError("Native effect ID does not uniquely match the MLT service")
    return effect_id
