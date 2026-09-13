"""Typed calls to the opt-in, in-process Kdenlive bridge. Never retries edits."""

import json
import os
import re
import socket
import time
import uuid

MAX_FRAME = 1024 * 1024
METHODS = {"handshake", "project_state", "insert_clip", "move_clip", "undo", "redo"}


class BridgeError(RuntimeError):
    pass


class NativeBridge:
    def __init__(self, port, token, host_pid, timeout=5):
        if not 0 < port < 65536 or host_pid <= 0 or len(token) < 32:
            raise ValueError("Bridge needs a valid port, exact host PID and >=32 character token")
        if not 0 < timeout <= 30:
            raise ValueError("Bridge timeout must be in (0, 30]")
        self.port, self.token, self.host_pid, self.timeout = port, token, host_pid, timeout

    @classmethod
    def from_env(cls):
        try:
            return cls(
                int(os.environ["DCC_KDENLIVE_BRIDGE_PORT"]),
                os.environ["DCC_KDENLIVE_BRIDGE_TOKEN"],
                int(os.environ["DCC_KDENLIVE_BRIDGE_HOST_PID"]),
            )
        except (KeyError, ValueError) as exc:
            raise BridgeError("native_bridge_not_configured") from exc

    def call(self, method, params=None):
        if method not in METHODS:
            raise ValueError("Unsupported native method")
        request_id = str(uuid.uuid4())
        request = {
            "protocol": 1,
            "id": request_id,
            "token": self.token,
            "host_pid": self.host_pid,
            "method": method,
            "params": params or {},
        }
        wire = json.dumps(request, allow_nan=False).encode("utf-8") + b"\n"
        if len(wire) > MAX_FRAME:
            raise ValueError("Native request exceeds frame limit")
        deadline = time.monotonic() + self.timeout
        try:
            with socket.create_connection(("127.0.0.1", self.port), self.timeout) as connection:
                connection.sendall(wire)
                data = bytearray()
                while b"\n" not in data:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise socket.timeout()
                    connection.settimeout(remaining)
                    chunk = connection.recv(min(65536, MAX_FRAME + 1 - len(data)))
                    if not chunk:
                        raise BridgeError(
                            "native_connection_lost: read state before retrying an edit"
                        )
                    data.extend(chunk)
                    if len(data) > MAX_FRAME:
                        raise BridgeError("native_response_too_large")
                response = json.loads(data.decode("utf-8"))
        except (OSError, ValueError) as exc:
            # Do not echo request/token or automatically replay an uncertain mutation.
            raise BridgeError("native_transport_error: read state before retrying an edit") from exc
        if (
            not isinstance(response, dict)
            or response.get("protocol") != 1
            or response.get("id") != request_id
            or response.get("host_pid") != self.host_pid
        ):
            raise BridgeError("native_identity_mismatch")
        if "error" in response:
            code = response["error"]
            if not isinstance(code, str) or not re.fullmatch(r"[a-z_]{1,80}", code):
                code = "invalid_native_error"
            raise BridgeError(code)
        if not isinstance(response.get("result"), dict):
            raise BridgeError("invalid_native_result")
        return response["result"]


def handshake():
    return NativeBridge.from_env().call("handshake")


def project_state():
    return NativeBridge.from_env().call("project_state")


def _edit(method, expected_revision, **params):
    if not isinstance(expected_revision, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_revision
    ):
        raise ValueError("Use the revision from a fresh native project_state")
    for key in ("track_id", "clip_id", "position"):
        if key in params and (type(params[key]) is not int or not 0 <= params[key] <= 2147483647):
            raise ValueError("{} must be a non-negative 32-bit frame or ID".format(key))
    params["expected_revision"] = expected_revision
    return NativeBridge.from_env().call(method, params)


def insert_clip(bin_id, track_id, position, expected_revision):
    if not isinstance(bin_id, str) or not bin_id:
        raise ValueError("bin_id must identify an imported native bin clip")
    return _edit(
        "insert_clip", expected_revision, bin_id=bin_id, track_id=track_id, position=position
    )


def move_clip(clip_id, track_id, position, expected_revision):
    return _edit(
        "move_clip", expected_revision, clip_id=clip_id, track_id=track_id, position=position
    )


def undo(expected_revision):
    return _edit("undo", expected_revision)


def redo(expected_revision):
    return _edit("redo", expected_revision)
