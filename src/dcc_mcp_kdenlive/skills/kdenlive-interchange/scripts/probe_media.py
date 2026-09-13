"""Inspect actual audio/video streams and format using FFprobe."""

from dcc_mcp_kdenlive.media import probe_media


def main(**kwargs):
    return probe_media(**kwargs)
