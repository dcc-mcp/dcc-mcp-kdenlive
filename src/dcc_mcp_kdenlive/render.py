"""MLT renders are core-owned async jobs with cooperative process cancellation."""

import os
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .media import probe_media
from .project import Project
from .runtime import executable, run_native

PRESETS = {
    "mp4": ["vcodec=libx264", "acodec=aac", "crf=18", "preset=medium"],
    "webm": ["vcodec=libvpx-vp9", "acodec=libopus", "crf=30", "b=0"],
    "mov": ["vcodec=prores_ks", "acodec=pcm_s16le", "profile=3"],
    "wav": ["vn=1", "acodec=pcm_s16le"],
}


def render_project(path, output_path, preset="mp4", start=0, end=0, timeout=3600):
    from dcc_mcp_core.skills_helper import check_dcc_cancelled

    if preset not in PRESETS:
        raise ValueError("Unknown render preset")
    if (
        any(isinstance(value, bool) or not isinstance(value, int) for value in (start, end))
        or start < 0
        or end < start
    ):
        raise ValueError("Specify an explicit inclusive render frame range")
    output = Path(output_path).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(str(output))
    project = Project(path)
    if output.suffix.lower() != "." + preset:
        raise ValueError("Output extension must match the selected preset")
    # Render a frozen document; never let the engine re-read a concurrently edited source.
    root_path = Path(project.root.get("root") or str(project.path.parent))
    if not root_path.is_absolute():
        root_path = project.path.parent / root_path
    project.root.set("root", str(root_path.resolve()))
    # Project files do not contain a render consumer. Reject imported consumers
    # with arbitrary output targets and supply our one owned output instead.
    for consumer in project.root.findall("consumer"):
        project.root.remove(consumer)
    with tempfile.TemporaryDirectory(
        prefix=".kdenlive-render-", dir=str(output.parent)
    ) as directory:
        frozen = Path(directory) / "project.mlt"
        frozen.write_bytes(ET.tostring(project.root, encoding="utf-8", xml_declaration=True))
        temporary = Path(directory) / ("output." + preset)
        run_native(
            [
                executable("melt"),
                str(frozen),
                "in={}".format(start),
                "out={}".format(end),
                "-consumer",
                "avformat:" + str(temporary),
                "real_time=-1",
                "threads=2",
            ]
            + PRESETS[preset],
            timeout=timeout,
            cancel=check_dcc_cancelled,
        )
        check_dcc_cancelled()
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise RuntimeError("Renderer returned without a nonempty artifact")
        probe = probe_media(str(temporary))
        if not probe.get("streams"):
            raise RuntimeError("Rendered artifact has no decodable streams")
        os.link(str(temporary), str(output))
        return {
            "path": str(output.resolve()),
            "bytes": output.stat().st_size,
            "source_sha256": project.sha256,
            "status": "completed",
            "streams": probe["streams"],
            "format": {
                key: value for key, value in probe.get("format", {}).items() if key != "filename"
            },
        }
