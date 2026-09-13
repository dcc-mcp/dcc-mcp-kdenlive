"""Remove an ungrouped timeline item, leaving a gap or rippling that playlist."""

from dcc_mcp_kdenlive.project import remove_item


def main(**kwargs):
    return remove_item(**kwargs)
