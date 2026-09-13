---
name: kdenlive-effects
description: Attach an installed MLT audio/video effect to a producer or track. Producer effects affect all its uses. Update effect or composition parameters, including native MLT keyframe strings. Remove a user effect while preserving internal mixer filters. Add a composition between two tractor tracks for an inclusive frame range.
compatibility: "Python 3.7+, dcc-mcp-core 0.20.28+, Kdenlive/MLT installed for native operations"
metadata:
  dcc-mcp:
    dcc: kdenlive
    layer: domain
    version: "0.1.0" # x-release-please-version
    tools: tools.yaml
    tags: [kdenlive, video, pipeline]
    search-hint: "Kdenlive effects add_effect set_properties remove_effect add_transition"
---

# Kdenlive Effects

Discover and describe tools before calls. File edits create new artifacts; inspect the returned file before opening it in the editor. Supply expected_sha256 for revision fencing. Frames are integers; end frames are inclusive. File results are not live editor readback.

Grouped clips, nested sequences, timeline model operations and other editor-only features use the shared ui-control skill on a GUI instance bound to an exact Kdenlive PID and HWND. Report provider=dcc-cua and its runtime version before UI observation. Use snapshot -> act -> snapshot and stop the session when done. Never switch to another UI provider or retry after a policy rejection or user interruption.

For rendering, poll the core job ID until terminal; a timeout is not completion. Cancellation terminates the owned render process and cleans partial output.
