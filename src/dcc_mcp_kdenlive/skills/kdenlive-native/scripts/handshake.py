"""Read native bridge identity and implemented capabilities."""

from dcc_mcp_kdenlive.native import handshake


def main(**kwargs):
    return handshake(**kwargs)
