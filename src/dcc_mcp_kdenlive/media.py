"""Media inspection and portable subtitle interchange."""

import json
from pathlib import Path

from .runtime import executable, run_native
from .storage import publish


def probe_media(path):
    path = Path(path).resolve(strict=True)
    return json.loads(
        run_native(
            [
                executable("ffprobe"),
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ]
        )
    )


def write_subtitles(output_path, cues):
    def timestamp(milliseconds):
        hours, remainder = divmod(milliseconds, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, ms = divmod(remainder, 1000)
        return "{:02}:{:02}:{:02},{:03}".format(hours, minutes, seconds, ms)

    lines = []
    previous = 0
    for index, cue in enumerate(cues, 1):
        start, end, text = cue["start_ms"], cue["end_ms"], cue["text"]
        if (
            any(isinstance(value, bool) or not isinstance(value, int) for value in (start, end))
            or start < previous
            or end <= start
        ):
            raise ValueError(
                "Subtitles must be ordered, non-overlapping, positive-duration integer ranges"
            )
        if not text.strip() or "\n\n" in text.replace("\r\n", "\n"):
            raise ValueError("Subtitle text must not contain blank separator lines")
        lines.append("{}\n{} --> {}\n{}\n".format(index, timestamp(start), timestamp(end), text))
        previous = end
    return publish(output_path, ("\n".join(lines) + "\n").encode("utf-8"))
