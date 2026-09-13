"""Discover actual installed MLT services and Kdenlive asset definitions."""

import os
import re
from pathlib import Path

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
