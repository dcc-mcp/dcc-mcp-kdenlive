"""Split an ungrouped clip at an offset while preserving source ranges."""

from dcc_mcp_kdenlive.project import split_clip


def main(**kwargs):
    return split_clip(**kwargs)
