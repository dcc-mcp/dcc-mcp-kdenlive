"""Insert an existing bin clip using the native undoable timeline command."""

from dcc_mcp_kdenlive.native import insert_clip


def main(**kwargs):
    return insert_clip(**kwargs)
