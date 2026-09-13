"""Create a Kdenlive project with audio and video tracks."""

from dcc_mcp_kdenlive.project import create_project


def main(**kwargs):
    return create_project(**kwargs)
