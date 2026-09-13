"""Attach an installed MLT audio/video effect to a producer or track. Producer effects affect all its uses."""

from dcc_mcp_kdenlive.project import add_effect


def main(**kwargs):
    return add_effect(**kwargs)
