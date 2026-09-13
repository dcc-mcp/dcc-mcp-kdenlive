"""Report installed renderer tools and running Kdenlive processes without installing or starting the editor."""

from dcc_mcp_kdenlive.runtime import get_status


def main(**kwargs):
    return get_status(**kwargs)
