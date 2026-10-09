---
name: kdenlive-export
description: Render an explicit frame range through MLT to MP4, WebM, ProRes MOV or WAV, or one RGBA PNG frame. Poll core jobs_get_status; use jobs_cancel to cancel.
compatibility: "Python 3.7+, dcc-mcp-core 0.20.28+, Kdenlive/MLT installed for native operations"
metadata:
  dcc-mcp:
    dcc: kdenlive
    layer: domain
    version: "0.1.4" # x-release-please-version
    tools: tools.yaml
    tags: [kdenlive, video, pipeline]
    search-hint: "Kdenlive export render_project"
---

# Kdenlive Export

Discover and describe tools before calls. File edits create new artifacts; inspect the returned file before opening it in the editor. Supply expected_sha256 for revision fencing. Frames are integers; end frames are inclusive. File results are not live editor readback.

Grouped clips, nested sequences, timeline model operations and other editor-only features use the shared ui-control skill on a GUI instance bound to an exact Kdenlive PID and HWND. Report provider=dcc-cua and its runtime version before UI observation. Use snapshot -> act -> snapshot and stop the session when done. Never switch to another UI provider or retry after a policy rejection or user interruption.

For rendering, poll the core job ID until terminal; a timeout is not completion. Cancellation terminates the owned render process and cleans partial output.

For a lossless encoded still, set preset to `png` and supply the same nonnegative frame for `start` and `end`. The project width and height must each be at most 4096. The tool exports one 8-bit RGBA PNG, checks its header and native stream dimensions, and publishes without replacing an existing file. PNG encoding does not guarantee identical rendering across fonts, displays or project changes; compare decoded pixels when validating those differences.
