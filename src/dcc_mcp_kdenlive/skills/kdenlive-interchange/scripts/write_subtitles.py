"""Write validated, ordered subtitle cues to a new UTF-8 SRT file for editor import."""

from dcc_mcp_kdenlive.media import write_subtitles


def main(**kwargs):
    return write_subtitles(**kwargs)
