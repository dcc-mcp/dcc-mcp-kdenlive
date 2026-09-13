import os

import pytest

from dcc_mcp_kdenlive.project import add_media, create_project, insert_clip

os.environ["DCC_MCP_DISABLE_DEFAULT_SKILL_PATHS"] = "1"
os.environ["DCC_MCP_DISABLE_TELEMETRY"] = "1"


@pytest.fixture
def project(tmp_path):
    create_project(
        str(tmp_path / "empty.kdenlive"), width=320, height=180, video_tracks=1, audio_tracks=0
    )
    media = add_media(
        str(tmp_path / "empty.kdenlive"),
        str(tmp_path / "media.kdenlive"),
        "#ff0000",
        25,
        kind="color",
    )
    insert_clip(
        str(tmp_path / "media.kdenlive"),
        str(tmp_path / "timeline.kdenlive"),
        "track_0_0",
        media["producer_id"],
        0,
        0,
        24,
    )
    return tmp_path / "timeline.kdenlive"
