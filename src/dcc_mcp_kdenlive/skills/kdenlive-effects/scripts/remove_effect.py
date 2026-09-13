"""Remove a user effect while preserving internal mixer filters."""

from dcc_mcp_kdenlive.project import remove_effect


def main(**kwargs):
    return remove_effect(**kwargs)
