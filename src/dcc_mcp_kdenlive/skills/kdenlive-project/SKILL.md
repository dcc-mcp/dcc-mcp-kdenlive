---
name: kdenlive-project
description: Create a Kdenlive project with audio and video tracks. Inspect the file profile, bin, tracks, clips and effects; does not read live editor state. Validate XML references, IDs, frame rate and entry ranges. Replace project guide markers in a new file.
compatibility: "Python 3.7+, dcc-mcp-core 0.20.28+, Kdenlive/MLT installed for native operations"
metadata:
  dcc-mcp:
    dcc: kdenlive
    layer: domain
    version: "0.1.3" # x-release-please-version
    tools: tools.yaml
    tags: [kdenlive, video, pipeline]
    search-hint: "Kdenlive project create_project inspect_project validate_project set_guides"
---

# Kdenlive Project

Discover and describe tools before calls. File edits create new artifacts; inspect the returned file before opening it in the editor. Supply expected_sha256 for revision fencing. Frames are integers; end frames are inclusive. File results are not live editor readback.

Grouped clips, nested sequences, timeline model operations and other editor-only features use the shared ui-control skill on a GUI instance bound to an exact Kdenlive PID and HWND. Report provider=dcc-cua and its runtime version before UI observation. Use snapshot -> act -> snapshot and stop the session when done. Never switch to another UI provider or retry after a policy rejection or user interruption.

For rendering, poll the core job ID until terminal; a timeout is not completion. Cancellation terminates the owned render process and cleans partial output.


## Portable native bundles

`package_project` accepts explicit media roots already authorized for the task. It copies only referenced regular media, uses content-addressed filenames to avoid basename collisions, and records bytes and SHA-256 without private source paths. Media resources are relative; the native root is empty so Kdenlive can recover the directory from the opened document's location instead of the editor's launch directory. Existing destinations are never replaced. Cancellation/error removes staging, not the source. Linux uses atomic no-replace directory publication; platforms without that primitive fail closed. File/color producers and bounded audited effects are supported; indirect title/effect dependencies, remote media and symlinks are rejected. These limits are not a sandbox against hostile parsers or concurrent directory attackers. Open the packaged native project and render it through MCP after packaging; structural/hash checks alone are not editor or render acceptance.
