"""Apply the bridge overlay to an exact, clean upstream checkout (never installs)."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(source):
    source = Path(source).resolve()
    lock = json.loads((ROOT / "native/upstream.json").read_text())
    head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"]).decode().strip()
    if head != lock["commit"]:
        raise ValueError("Upstream commit does not match native/upstream.json")
    dirty = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"])
    if dirty.strip():
        raise ValueError("Use a clean upstream checkout; refusing to overwrite local changes")
    core = source / "src/core.cpp"
    text = core.read_text(encoding="utf-8")
    anchor = "    connect(this, &Core::displayBinMessage, this, &Core::displayBinMessagePrivate);"
    if text.count(anchor) != 1:
        raise ValueError("Upstream startup hook changed")
    text = text.replace(
        anchor, anchor + "\n    QTimer::singleShot(0, m_mainWindow, []() { startDccBridge(); });"
    )
    text = "extern void startDccBridge();\n" + text
    cmake = source / "src/CMakeLists.txt"
    build = (
        cmake.read_text(encoding="utf-8")
        + """

# DCC-MCP bridge overlay; compiled into the exact pinned host, not a plugin ABI.
find_package(Qt6 REQUIRED COMPONENTS Network)
target_sources(kdenliveLib PRIVATE dccbridge/bridge_server.cpp dccbridge/kdenlive_bridge.cpp)
target_include_directories(kdenliveLib PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/dccbridge)
target_link_libraries(kdenliveLib PUBLIC Qt6::Network)
"""
    )
    target = source / "src/dccbridge"
    target.mkdir()
    for name in ("bridge_server.h", "bridge_server.cpp", "kdenlive_bridge.cpp"):
        shutil.copy2(str(ROOT / "native" / name), str(target / name))
    core.write_text(text, encoding="utf-8")
    cmake.write_text(build, encoding="utf-8")
    print("Prepared Kdenlive {} with bridge protocol {}".format(lock["tag"], lock["protocol"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    prepare(parser.parse_args().source)
