"""Inspect the file profile, bin, tracks, clips and effects; does not read live editor state."""

from dcc_mcp_kdenlive.project import inspect_project


def main(**kwargs):
    return inspect_project(**kwargs)
