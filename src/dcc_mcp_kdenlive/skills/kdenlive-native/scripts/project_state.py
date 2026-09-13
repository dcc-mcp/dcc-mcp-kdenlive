"""Read the live editor timeline, clip IDs and revision."""

from dcc_mcp_kdenlive.native import project_state


def main(**kwargs):
    return project_state(**kwargs)
