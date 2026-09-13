"""Update effect or composition parameters, including native MLT keyframe strings."""

from dcc_mcp_kdenlive.project import set_properties


def main(**kwargs):
    return set_properties(**kwargs)
