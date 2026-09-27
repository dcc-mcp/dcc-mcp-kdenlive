---
name: kdenlive-interchange
description: Inspect actual audio/video streams and format using FFprobe. Write validated, ordered subtitle cues to a new UTF-8 SRT file for editor import.
compatibility: "Python 3.7+, dcc-mcp-core 0.20.28+, Kdenlive/MLT installed for native operations"
metadata:
  dcc-mcp:
    dcc: kdenlive
    layer: domain
    version: "0.1.1" # x-release-please-version
    tools: tools.yaml
    tags: [kdenlive, video, pipeline]
    search-hint: "Kdenlive interchange probe_media write_subtitles"
---

# Kdenlive Interchange

Discover and describe tools before calls. File edits create new artifacts; inspect the returned file before opening it in the editor. Supply expected_sha256 for revision fencing. Frames are integers; end frames are inclusive. File results are not live editor readback.

Grouped clips, nested sequences, timeline model operations and other editor-only features use the shared ui-control skill on a GUI instance bound to an exact Kdenlive PID and HWND. Report provider=dcc-cua and its runtime version before UI observation. Use snapshot -> act -> snapshot and stop the session when done. Never switch to another UI provider or retry after a policy rejection or user interruption.

For rendering, poll the core job ID until terminal; a timeout is not completion. Cancellation terminates the owned render process and cleans partial output.
