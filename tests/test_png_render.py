import struct
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from dcc_mcp_kdenlive import render
from dcc_mcp_kdenlive.project import create_project


def png_bytes(width=16, height=16, color=6):
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\0\0\xff" * width) * height))
        + chunk(b"IEND", b"")
    )


@pytest.fixture
def png_case(tmp_path, monkeypatch):
    source = tmp_path / "source.kdenlive"
    create_project(str(source), width=16, height=16)
    state = {
        "calls": [],
        "png": png_bytes(),
        "probe": {
            "streams": [{"codec_name": "png", "width": 16, "height": 16, "pix_fmt": "rgba"}],
            "format": {"filename": "private-staged-name", "format_name": "png_pipe"},
        },
    }

    def run(command, **kwargs):
        state["calls"].append(command)
        frozen = ET.parse(command[1]).getroot()
        assert frozen.get("root") == str(tmp_path)
        target = next(x for x in command if x.startswith("avformat:"))
        Path(target[len("avformat:") :]).write_bytes(state["png"])

    monkeypatch.setattr(render, "executable", lambda name: name)
    monkeypatch.setattr(render, "run_native", run)
    monkeypatch.setattr(render, "probe_media", lambda path: state["probe"])
    return source, tmp_path / "frame.png", state


def test_png_single_frame_rgba_readback_and_source_preservation(png_case):
    source, output, state = png_case
    before = source.read_bytes()
    result = render.render_project(str(source), str(output), preset="png", start=3, end=3)
    assert output.read_bytes() == state["png"]
    assert source.read_bytes() == before
    assert result["path"] == str(output)
    assert result["format"] == {"format_name": "png_pipe"}
    assert len(state["calls"]) == 1
    assert {"in=3", "out=3", "f=image2", "vcodec=png", "an=1", "pix_fmt=rgba", "update=1"}.issubset(
        state["calls"][0]
    )


def test_png_rejects_multi_frame_before_native_call(png_case):
    source, output, state = png_case
    with pytest.raises(ValueError, match="exactly one frame"):
        render.render_project(str(source), str(output), preset="png", start=0, end=1)
    assert state["calls"] == [] and not output.exists()


def test_png_rejects_native_position_overflow_before_native_call(png_case):
    source, output, state = png_case
    with pytest.raises(ValueError, match="native position range"):
        render.render_project(str(source), str(output), preset="png", start=2**64, end=2**64)
    assert state["calls"] == [] and not output.exists()


@pytest.mark.parametrize("dimension,value", [("width", "4097"), ("height", "0"), ("width", "nan")])
def test_png_rejects_invalid_dimensions_before_native_call(png_case, dimension, value):
    source, output, state = png_case
    tree = ET.parse(source)
    tree.getroot().find("profile").set(dimension, value)
    tree.write(source)
    with pytest.raises(ValueError, match="PNG export"):
        render.render_project(str(source), str(output), preset="png", start=0, end=0)
    assert state["calls"] == [] and not output.exists()


@pytest.mark.parametrize("payload", [b"not a PNG", png_bytes(width=17), png_bytes(color=2)])
def test_png_rejects_native_format_or_size_mismatch_before_publication(png_case, payload):
    source, output, state = png_case
    state["png"] = payload
    with pytest.raises(RuntimeError, match="Native PNG"):
        render.render_project(str(source), str(output), preset="png", start=0, end=0)
    assert not output.exists()
    assert list(output.parent.glob(".kdenlive-render-*")) == []


def test_png_rejects_probe_mismatch_before_publication(png_case):
    source, output, state = png_case
    state["probe"]["streams"][0]["pix_fmt"] = "rgb24"
    with pytest.raises(RuntimeError, match="stream readback"):
        render.render_project(str(source), str(output), preset="png", start=0, end=0)
    assert not output.exists()


def test_png_existing_destination_is_preserved(png_case):
    source, output, state = png_case
    output.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        render.render_project(str(source), str(output), preset="png", start=0, end=0)
    assert output.read_bytes() == b"original" and state["calls"] == []


def test_cancellation_during_readback_prevents_publication(png_case, monkeypatch):
    from dcc_mcp_core import skills_helper

    source, output, state = png_case
    cancelled = [False]

    def probe(path):
        cancelled[0] = True
        return state["probe"]

    def check():
        if cancelled[0]:
            raise RuntimeError("test cancellation after readback")

    monkeypatch.setattr(render, "probe_media", probe)
    monkeypatch.setattr(skills_helper, "check_dcc_cancelled", check)
    with pytest.raises(RuntimeError, match="test cancellation"):
        render.render_project(str(source), str(output), preset="png", start=0, end=0)
    assert not output.exists()
