import json
import urllib.request

import pytest

from dcc_mcp_kdenlive.project import Project
from dcc_mcp_kdenlive.server import KdenliveServer


def test_http_mcp_discover_load_call_and_readback(tmp_path):
    server = KdenliveServer(
        gateway_port=0,
        enable_gateway_failover=False,
        enable_telemetry=False,
        registry_dir=str(tmp_path / "registry"),
    )
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

    def rpc(method, params):
        request = urllib.request.Request(
            server.mcp_url,
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
            headers,
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.headers.get("Mcp-Session-Id"):
                headers["Mcp-Session-Id"] = response.headers["Mcp-Session-Id"]
            result = json.loads(response.read())
        assert "error" not in result, result
        return result["result"]

    try:
        server.register_builtin_actions()
        server.start()
        rpc(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "kdenlive-test", "version": "1"},
            },
        )
        result = rpc(
            "tools/call", {"name": "load_skill", "arguments": {"skill_name": "kdenlive-project"}}
        )
        assert not result.get("isError"), result
        assert "kdenlive_project__create_project" in str(result)
        assert rpc("tools/list", {})["tools"]
        target = tmp_path / "over-mcp.kdenlive"
        result = rpc(
            "tools/call",
            {"name": "kdenlive_project__create_project", "arguments": {"output_path": str(target)}},
        )
        assert not result.get("isError"), result
        assert Project(target).validate()["valid"]
        invalid = rpc(
            "tools/call",
            {"name": "kdenlive_project__create_project", "arguments": {"output_path": str(target)}},
        )
        assert invalid.get("isError"), invalid
    finally:
        server.stop()
    assert not server.is_running


def test_gui_requires_both_identity_fields():
    with pytest.raises(ValueError, match="both exact"):
        KdenliveServer(dcc_pid=123)


def test_port_environment_respected(monkeypatch):
    monkeypatch.setenv("DCC_MCP_KDENLIVE_PORT", "12345")
    server = KdenliveServer(gateway_port=0, enable_gateway_failover=False)
    assert server._options.port == 12345
    assert server._options.instance_type == "standalone"
