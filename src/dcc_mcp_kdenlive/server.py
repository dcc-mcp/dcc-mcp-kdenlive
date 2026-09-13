"""Composition root using core lifecycle, discovery, jobs and UI control."""

import os
from pathlib import Path

from dcc_mcp_core import DccServerBase, DccServerOptions, HostExecutionBridge

from . import __version__
from .runtime import validate_host


class KdenliveServer(DccServerBase):
    def __init__(self, port=None, dcc_pid=None, dcc_window_handle=None, dcc_version=None, **kwargs):
        if (dcc_pid is None) != (dcc_window_handle is None):
            raise ValueError("GUI mode requires both exact PID and window handle")
        if dcc_pid is not None:
            validate_host(dcc_pid)
            if dcc_window_handle <= 0:
                raise ValueError("Window handle must be positive")
        if os.environ.get("DCC_KDENLIVE_BRIDGE_PORT"):
            from .native import NativeBridge

            bridge = NativeBridge.from_env()
            if bridge.host_pid != dcc_pid:
                raise ValueError("Native bridge must match the server's bound GUI host PID")
            info = bridge.call("handshake")
            if info.get("host_version") != "26.08.1":
                raise ValueError("Native bridge host version is not supported")
            if info.get("window_handle") != str(dcc_window_handle):
                raise ValueError("Native bridge window does not match the bound GUI HWND")
        options = DccServerOptions.from_env(
            "kdenlive",
            Path(__file__).parent / "skills",
            port=port,
            server_name="dcc-mcp-kdenlive",
            adapter_version=__version__,
            instance_type="gui" if dcc_pid is not None else "standalone",
            dcc_pid=dcc_pid,
            dcc_window_handle=dcc_window_handle,
            dcc_window_title="Kdenlive" if dcc_pid is not None else None,
            dcc_version=dcc_version,
            execution_bridge=HostExecutionBridge(dispatcher=None),
            **kwargs,
        )
        super().__init__(options=options)

    def _version_string(self):
        return "unknown"
