"""Build deterministic agent skill bundle, wheel manifest and checksums."""

import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = re.search(
        r'__version__ = "([^"]+)"', (ROOT / "src/dcc_mcp_kdenlive/__init__.py").read_text()
    )[1]
    dist = ROOT / "dist"
    wheels = list(dist.glob("dcc_mcp_kdenlive-{}-*.whl".format(version)))
    if len(wheels) != 1:
        raise ValueError("Build exactly one version-matched wheel first")
    skills = ROOT / "src/dcc_mcp_kdenlive/skills"
    with zipfile.ZipFile(
        str(dist / ("dcc-mcp-kdenlive-" + version + "-skills.zip")), "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for path in sorted(skills.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                info = zipfile.ZipInfo(
                    path.relative_to(skills).as_posix(), date_time=(2020, 1, 1, 0, 0, 0)
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
    wheel = wheels[0]
    manifest = {
        "schema_version": 1,
        "dcc_type": "kdenlive",
        "adapter_version": version,
        "entry_point": "dcc-mcp-kdenlive serve",
        "requires_python": ">=3.7",
        "wheel": {
            "url": "https://github.com/dcc-mcp/dcc-mcp-kdenlive/releases/download/v{}/{}".format(
                version, wheel.name
            ),
            "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        },
        "host_bundled": False,
    }
    (dist / "install-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name
        for path in sorted(dist.iterdir())
        if path.is_file() and path.name != "SHA256SUMS"
    ]
    (dist / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
