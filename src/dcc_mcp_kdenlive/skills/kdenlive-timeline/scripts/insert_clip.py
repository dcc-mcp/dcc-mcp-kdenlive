"""Append a clip at or after the playlist end, inserting a gap when needed."""

from dcc_mcp_kdenlive.project import insert_clip


def main(**kwargs):
    return insert_clip(**kwargs)
