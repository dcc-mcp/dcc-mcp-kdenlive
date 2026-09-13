"""Discover all installed MLT services or describe one service and its parameters."""

from dcc_mcp_kdenlive.catalog import query_services


def main(**kwargs):
    return query_services(**kwargs)
