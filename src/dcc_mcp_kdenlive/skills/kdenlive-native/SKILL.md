---
name: kdenlive-native
description: Read and edit the live Kdenlive timeline through the opt-in C++ bridge with native undo and revision checks.
compatibility: "Python 3.7+, dcc-mcp-core 0.20.28+, bridge-enabled Kdenlive 26.08.1"
metadata:
  dcc-mcp:
    dcc: kdenlive
    layer: domain
    version: "0.1.0"
    tools: tools.yaml
    tags: [kdenlive, native, timeline]
    search-hint: "Kdenlive live native bridge timeline insert move undo redo"
---

# Kdenlive Native

Requires the separately built C++ host overlay. Stock Kdenlive does not provide
this endpoint. First handshake, then project_state. Use returned native IDs and
revision for each edit. Mutations return live readback and a new revision.
Frames are integers. Insert uses an existing bin clip; it may insert linked audio.
Move follows native grouping/link semantics. Undo/redo affect the host undo stack,
including human commands, so inspect state immediately before use.

A network timeout has an unknown edit outcome. Read fresh state; never automatically
replay mutations. No raw Python, C++, shell or QAction execution is exposed.
The Python tool performs IPC on a worker; the C++ server dispatches model operations
on the Qt GUI thread. Bridge secrets and endpoint come only from operator environment,
not tool parameters. Missing bridge or host identity fails closed; it does not
silently route through CUA. Advanced native capabilities remain unimplemented until
advertised by handshake and validated in the host.
