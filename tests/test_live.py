import os
import subprocess

import pytest

from dcc_mcp_kdenlive.render import render_project
from dcc_mcp_kdenlive.runtime import executable


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("KDENLIVE_LIVE_TEST") != "1", reason="Requires installed MLT/FFprobe"
)
def test_real_mlt_render(project, tmp_path):
    result = render_project(str(project), str(tmp_path / "result.mp4"), start=0, end=24, timeout=60)
    video = next(stream for stream in result["streams"] if stream["codec_type"] == "video")
    assert (video["width"], video["height"]) == (320, 180)
    assert abs(float(result["format"]["duration"]) - 1.0) < 0.1
    assert result["status"] == "completed"


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("KDENLIVE_LIVE_TEST") != "1", reason="Requires installed MLT/FFmpeg"
)
def test_real_mlt_png_nonzero_frame_and_full_decode(project, tmp_path):
    from dcc_mcp_kdenlive.project import add_media, insert_clip

    media = add_media(
        str(project), str(tmp_path / "blue-media.kdenlive"), "#0000ff", 25, kind="color"
    )
    timeline = tmp_path / "two-colors.kdenlive"
    insert_clip(
        str(tmp_path / "blue-media.kdenlive"),
        str(timeline),
        "track_0_0",
        media["producer_id"],
        25,
        0,
        24,
    )
    before = timeline.read_bytes()
    output = tmp_path / "blue-frame.png"
    result = render_project(str(timeline), str(output), preset="png", start=26, end=26, timeout=60)
    assert timeline.read_bytes() == before
    assert result["streams"][0]["codec_name"] == "png"
    decoded = subprocess.check_output(
        [
            executable("ffmpeg"),
            "-v",
            "error",
            "-i",
            str(output),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-threads",
            "1",
            "-",
        ],
        timeout=60,
    )
    assert decoded == b"\0\0\xff\xff" * (320 * 180)
