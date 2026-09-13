import json
import socket
import threading
import urllib.request
from contextlib import contextmanager

import pytest

from dcc_mcp_kdenlive.native import BridgeError, NativeBridge, insert_clip, move_clip, undo


@contextmanager
def endpoint(transform):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(3)
    calls = []

    def serve():
        with listener:
            connection, _ = listener.accept()
            with connection:
                request = json.loads(connection.makefile("rb").readline())
                calls.append(request)
                result = transform(request)
                if result is not None:
                    wire = json.dumps(result).encode() + b"\n"
                    connection.sendall(wire[:7])
                    connection.sendall(wire[7:])

    worker = threading.Thread(target=serve)
    worker.start()
    try:
        yield NativeBridge(listener.getsockname()[1], "a" * 32, 1234), calls
    finally:
        worker.join(5)
        assert not worker.is_alive()


def reply(request):
    return {"id": request["id"], "protocol": 1, "host_pid": 1234, "result": {"revision": "b" * 64}}


def test_round_trip():
    with endpoint(reply) as (client, calls):
        assert client.call("project_state")["revision"] == "b" * 64
    assert len(calls) == 1
    assert calls[0]["method"] == "project_state"


@pytest.mark.parametrize("field,value", [("host_pid", 99), ("protocol", 2), ("id", "wrong")])
def test_reject_wrong_identity(field, value):
    def wrong(request):
        result = reply(request)
        result[field] = value
        return result

    with endpoint(wrong) as (client, _):
        with pytest.raises(BridgeError, match="identity_mismatch"):
            client.call("project_state")


def test_lost_mutation_response_is_never_replayed():
    with endpoint(lambda request: None) as (client, calls):
        with pytest.raises(BridgeError, match="read state before retrying"):
            client.call("undo", {"expected_revision": "b" * 64})
    assert len(calls) == 1


def test_native_error_propagated():
    def rejected(request):
        result = reply(request)
        del result["result"]
        result["error"] = "stale_revision"
        return result

    with endpoint(rejected) as (client, _):
        with pytest.raises(BridgeError, match="stale_revision"):
            client.call("undo", {"expected_revision": "b" * 64})


def test_missing_config(monkeypatch):
    monkeypatch.delenv("DCC_KDENLIVE_BRIDGE_PORT", raising=False)
    with pytest.raises(BridgeError, match="not_configured"):
        NativeBridge.from_env()


@pytest.mark.parametrize("position", [-1, 1.5, True, 2147483648])
def test_invalid_frame_rejected_before_transport(position):
    with pytest.raises(ValueError):
        move_clip(1, 2, position, "a" * 64)


def test_requires_revision_and_bin_id():
    with pytest.raises(ValueError):
        undo("")
    with pytest.raises(ValueError):
        insert_clip("", 1, 0, "a" * 64)


def test_mcp_native_skill_calls_tcp_bridge(tmp_path, monkeypatch):
    from dcc_mcp_kdenlive.server import KdenliveServer

    monkeypatch.delenv("DCC_KDENLIVE_BRIDGE_PORT", raising=False)
    server = KdenliveServer(
        gateway_port=0,
        enable_gateway_failover=False,
        enable_telemetry=False,
        registry_dir=str(tmp_path / "registry"),
    )
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

    def rpc(method, params):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        with urllib.request.urlopen(
            urllib.request.Request(server.mcp_url, body, headers), timeout=10
        ) as response:
            if response.headers.get("Mcp-Session-Id"):
                headers["Mcp-Session-Id"] = response.headers["Mcp-Session-Id"]
            return json.loads(response.read())["result"]

    try:
        server.register_builtin_actions()
        server.start()
        rpc(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "native-test", "version": "1"},
            },
        )
        loaded = rpc(
            "tools/call", {"name": "load_skill", "arguments": {"skill_name": "kdenlive-native"}}
        )
        assert not loaded.get("isError"), loaded
        with endpoint(reply) as (client, calls):
            # Test-only fake endpoint; not a live Kdenlive acceptance claim.
            monkeypatch.setenv("DCC_KDENLIVE_BRIDGE_PORT", str(client.port))
            monkeypatch.setenv("DCC_KDENLIVE_BRIDGE_TOKEN", client.token)
            monkeypatch.setenv("DCC_KDENLIVE_BRIDGE_HOST_PID", str(client.host_pid))
            result = rpc("tools/call", {"name": "kdenlive_native__project_state", "arguments": {}})
            assert not result.get("isError"), result
            assert "b" * 64 in str(result)
        assert len(calls) == 1
    finally:
        server.stop()


def test_server_rejects_unbound_bridge(monkeypatch):
    from dcc_mcp_kdenlive.server import KdenliveServer

    monkeypatch.setenv("DCC_KDENLIVE_BRIDGE_PORT", "12345")
    monkeypatch.setenv("DCC_KDENLIVE_BRIDGE_TOKEN", "a" * 32)
    monkeypatch.setenv("DCC_KDENLIVE_BRIDGE_HOST_PID", "1234")
    with pytest.raises(ValueError, match="bound GUI host PID"):
        KdenliveServer()
