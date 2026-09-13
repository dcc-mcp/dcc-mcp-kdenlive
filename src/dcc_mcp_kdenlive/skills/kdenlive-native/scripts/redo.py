"""Redo the next host command, only against a fresh revision."""

from dcc_mcp_kdenlive.native import redo


def main(**kwargs):
    return redo(**kwargs)
