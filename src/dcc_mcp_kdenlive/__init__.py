"""Kdenlive adapter; host discovery is lazy."""

__version__ = "0.1.1"  # x-release-please-version


def __getattr__(name):
    if name == "KdenliveServer":
        from .server import KdenliveServer

        return KdenliveServer
    raise AttributeError(name)
