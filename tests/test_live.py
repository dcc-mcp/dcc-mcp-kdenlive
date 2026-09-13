import os

import pytest

from dcc_mcp_kdenlive.render import render_project


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
