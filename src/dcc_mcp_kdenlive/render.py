"""MLT renders are core-owned async jobs with cooperative process cancellation."""

import os
import struct
import tempfile
import zlib
from pathlib import Path

from .media import probe_media
from .project import Project
from .runtime import executable, run_native
from .storage import xml_bytes

PRESETS = {
    "mp4": ["vcodec=libx264", "acodec=aac", "crf=18", "preset=medium"],
    "webm": ["vcodec=libvpx-vp9", "acodec=libopus", "crf=30", "b=0"],
    "mov": ["vcodec=prores_ks", "acodec=pcm_s16le", "profile=3"],
    "wav": ["vn=1", "acodec=pcm_s16le"],
    "png": ["f=image2", "vcodec=png", "an=1", "pix_fmt=rgba", "update=1"],
}


def png_dimensions(project):
    profile = project.root.find("profile")
    try:
        width, height = int(profile.get("width")), int(profile.get("height"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("PNG export requires integer project dimensions") from exc
    if not (1 <= width <= 4096 and 1 <= height <= 4096):
        raise ValueError("PNG export dimensions must each be between 1 and 4096")
    return width, height


def verify_png(path, dimensions, probe):
    with path.open("rb") as stream:
        header = stream.read(33)
    if (
        len(header) != 33
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or header[8:16] != b"\x00\x00\x00\rIHDR"
        or zlib.crc32(header[12:29]) != struct.unpack(">I", header[29:33])[0]
    ):
        raise RuntimeError("Native PNG export has an invalid image header")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", header[16:29]
    )
    if (width, height) != dimensions or (depth, color, compression, filtering, interlace) != (
        8,
        6,
        0,
        0,
        0,
    ):
        raise RuntimeError("Native PNG export differs from the requested RGBA frame")
    streams = probe.get("streams", [])
    if len(streams) != 1 or any(
        streams[0].get(key) != value
        for key, value in {
            "codec_name": "png",
            "width": width,
            "height": height,
            "pix_fmt": "rgba",
        }.items()
    ):
        raise RuntimeError("Native PNG stream readback differed")


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
    if preset == "png" and start != end:
        raise ValueError("PNG export requires exactly one frame: start must equal end")
    if preset == "png" and start > 2147483647:
        raise ValueError("PNG frame index exceeds the supported native position range")
    output = Path(output_path).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(str(output))
    project = Project(path)
    dimensions = png_dimensions(project) if preset == "png" else None
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
        frozen.write_bytes(xml_bytes(project.root))
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
        if preset == "png":
            verify_png(temporary, dimensions, probe)
        check_dcc_cancelled()
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
