"""Package an authorized project and its explicit media into a portable native bundle."""

from dcc_mcp_kdenlive.packaging import package_project


def main(**kwargs):
    return package_project(**kwargs)
