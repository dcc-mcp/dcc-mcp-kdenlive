"""Undo the latest host command, only against a fresh revision."""

from dcc_mcp_kdenlive.native import undo


def main(**kwargs):
    return undo(**kwargs)
