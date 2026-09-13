import subprocess
import sys

import pytest

from dcc_mcp_kdenlive.media import write_subtitles
from dcc_mcp_kdenlive.runtime import run_native


def test_subprocess_timeout_and_error():
    with pytest.raises(TimeoutError):
        run_native([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.1)
    with pytest.raises(RuntimeError, match="Native command failed"):
        run_native([sys.executable, "-c", "raise SystemExit(3)"])


def test_cancellation_reaps_child(monkeypatch):
    children = []
    real = subprocess.Popen

    def capture(*args, **kwargs):
        child = real(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", capture)

    def cancel():
        raise RuntimeError("cancelled")

    with pytest.raises(RuntimeError, match="cancelled"):
        run_native([sys.executable, "-c", "import time; time.sleep(5)"], cancel=cancel)
    assert children[0].poll() is not None


def test_subtitle_ranges(tmp_path):
    path = tmp_path / "sub.srt"
    write_subtitles(str(path), [{"start_ms": 0, "end_ms": 1000, "text": "Hello"}])
    assert "00:00:00,000 --> 00:00:01,000" in path.read_text()
    with pytest.raises(ValueError):
        write_subtitles(str(tmp_path / "bad.srt"), [{"start_ms": 20, "end_ms": 10, "text": "No"}])
