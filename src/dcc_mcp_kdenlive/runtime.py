"""Installed host discovery and bounded native process execution."""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import psutil


def executable(name):
    configured = os.environ.get("DCC_MCP_KDENLIVE_" + name.upper())
    if configured:
        path = Path(configured).resolve(strict=True)
        if not path.is_file():
            raise ValueError("Configured executable is not a file")
        return str(path)
    found = shutil.which(name) or (shutil.which("melt-7") if name == "melt" else None)
    if found:
        return found
    editor = os.environ.get("DCC_MCP_KDENLIVE_EXECUTABLE")
    if editor:
        candidate = Path(editor).parent / (name + (".exe" if os.name == "nt" else ""))
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError("Set DCC_MCP_KDENLIVE_{} or add {} to PATH".format(name.upper(), name))


def run_native(arguments, timeout=30, cancel=None):
    """No shell; bounded diagnostics; cancellation terminates and reaps the child."""
    if not 0 < timeout <= 86400:
        raise ValueError("Timeout must be in (0, 86400]")
    with tempfile.TemporaryFile() as log:
        child = subprocess.Popen(
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            deadline = time.monotonic() + timeout
            while child.poll() is None:
                if cancel:
                    cancel()
                if time.monotonic() >= deadline:
                    raise TimeoutError("Native operation timed out")
                time.sleep(0.05)
            log.seek(0)
            output = log.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            if child.returncode:
                raise RuntimeError(
                    "Native command failed ({}): {}".format(child.returncode, output[-4000:])
                )
            return output
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)


def get_status():
    from . import __version__

    programs = {}
    for name in ("melt", "ffprobe", "ffmpeg"):
        try:
            programs[name] = {"available": True, "path": executable(name)}
        except (ValueError, OSError) as error:
            programs[name] = {"available": False, "reason": str(error)}
    hosts = []
    for process in psutil.process_iter(["pid", "name", "exe"]):
        if (process.info["name"] or "").lower() in ("kdenlive", "kdenlive.exe"):
            hosts.append(process.info)
    return {
        "adapter_version": __version__,
        "programs": programs,
        "hosts": hosts,
        "editor_api": "dcc-cua/ui-control",
        "file_tools_ready": True,
        "host_control_ready": False,
        "host_control_note": "Requires a bound GUI instance and a fresh ui-control snapshot",
    }


def validate_host(pid):
    process = psutil.Process(pid)
    if process.name().lower() not in ("kdenlive", "kdenlive.exe"):
        raise ValueError("PID is not a Kdenlive process")
    return process
