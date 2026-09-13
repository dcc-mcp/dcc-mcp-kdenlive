"""Read the native parameters from an installed XML asset definition."""

from dcc_mcp_kdenlive.catalog import describe_asset


def main(**kwargs):
    return describe_asset(**kwargs)
