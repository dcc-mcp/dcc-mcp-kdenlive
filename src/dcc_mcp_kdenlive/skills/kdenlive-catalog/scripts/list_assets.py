"""List installed Kdenlive effects, transitions, titles, profiles, export presets, generators, lumas or LUTs."""

from dcc_mcp_kdenlive.catalog import list_assets


def main(**kwargs):
    return list_assets(**kwargs)
