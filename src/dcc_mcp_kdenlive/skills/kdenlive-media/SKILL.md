---
name: kdenlive-media
description: Add file media, native PNG stills, a color producer, or a Kdenlive title template to the project bin. Relink bin media and timeline instances to an existing local media file.
compatibility: "Python 3.7+, dcc-mcp-core 0.20.28+, Kdenlive/MLT installed for native operations"
metadata:
  dcc-mcp:
    dcc: kdenlive
    layer: domain
    version: "0.1.1" # x-release-please-version
    tools: tools.yaml
    tags: [kdenlive, video, pipeline]
    search-hint: "Kdenlive media add_media relink_media"
---

# Kdenlive Media

Discover and describe tools before calls. File edits create new artifacts; inspect the returned file before opening it in the editor. Supply expected_sha256 for revision fencing. Frames are integers; end frames are inclusive. File results are not live editor readback.

Grouped clips, nested sequences, timeline model operations and other editor-only features use the shared ui-control skill on a GUI instance bound to an exact Kdenlive PID and HWND. Report provider=dcc-cua and its runtime version before UI observation. Use snapshot -> act -> snapshot and stop the session when done. Never switch to another UI provider or retry after a policy rejection or user interruption.

For rendering, poll the core job ID until terminal; a timeout is not completion. Cancellation terminates the owned render process and cleans partial output.

## Native PNG stills

Use add_media with kind=image for a static local PNG. This selects qimage rather than the avformat file reader. The caller supplies its timeline duration. Input preflight bounds file size to64MiB, each declared edge to8192pixels and declared pixels to16777216, and checks the PNG signature/IHDR. This does not assert a full image decode or security isolation from hostile native files; native rendering and editor preview require separate qualification. QImage resource expansion syntax (`%`, `/.all.`, query suffixes and inline XML markers) is refused even when a matching PNG-named file exists. Other image formats and image sequences are not supported by this initial explicit kind. Existing file/color/title behavior is unchanged.

The same literal-resource check applies when relinking any affected qimage producer, including aliases. Relinking existing qimage JPEG or other native formats retains its prior format scope; only expansion syntax is refused. The initial PNG profile conservatively refuses a bare query marker too, though MLT7.30.0 only parses query start offsets in percent-based sequences.
