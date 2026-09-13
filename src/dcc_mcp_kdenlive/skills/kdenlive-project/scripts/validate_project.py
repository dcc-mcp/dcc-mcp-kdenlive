"""Validate XML references, IDs, frame rate and entry ranges."""

from dcc_mcp_kdenlive.project import validate_project


def main(**kwargs):
    return validate_project(**kwargs)
