# PNG still image import

Adding a PNG with `add_media(kind="image")` uses the native `qimage` producer.
The explicit kind addresses PNGs that render through `avformat` but show blank
frames during editor seeks. Existing `file`, `color` and `title` kinds retain
their behavior. The PNG profile checks signature/IHDR and declared dimensions:
33 bytes to 64 MiB, at most 8192 pixels on either edge, and at most 16,777,216
pixels. This is header preflight; it does not perform full decoding, capture an
immutable media snapshot or isolate a native parser from hostile files.

The exact canonical path stored in a `qimage` producer must be literal. Percent,
directory-expansion, query and inline-XML markers are rejected, including markers
in canonical parent directories. Relinking checks every affected `qimage` alias
before changing the graph. Existing `qimage` relinks retain their previous image
format scope. Unrelated `qimage` producers do not restrict `avformat` relinks.

## Publication checks

The complete five-file source packet was verified against base
`437aacad53ba0c0e9910508f9d19ce5ff991471c`: 15,251 UTF-8 bytes,
SHA-256 `36f875f1743f03d92856cbc7acbba8b7e8f8bae5fe0cae01ec8f7128e8be8c87`.
The publication candidate adds seven integration cases for mixed-service aliases,
safe alias rewrites with timing/effects preserved, unrelated aliases, canonical
parent markers and a real symlink normalized to a safe literal target.

On Windows / Python 3.12 / Core 0.20.41, the complete suite passed 101 tests with
7 explicit skips. These comprise the four existing platform/live-host skips and
three filenames Windows cannot create. All seven additional cases passed. Ruff
lint/format and Python 3.7 grammar checks for changed Python files passed.
These checks verify source, schema, graph authoring, publication fences and
packaged bytes; they are not a local Kdenlive editor or native QImage decode run.

## Source-author native qualification

[`png-image-import-qualification.json`](png-image-import-qualification.json)
preserves the source author's reported qualification separately from publication
checks. The source author reported 100 unit tests passing with one existing
live-host skip, a 29-event typed MCP pilot rendering 24 frames, and a 77-event
relocation proof comparing all 432 decoded RGBA frames and MP4 bytes while the
original project, package and media were unavailable. Source paths were reportedly
restored byte-exactly and both owned MCP hosts stopped.

The source author also reported reuse of earlier GUI seek and Save Copy/reopen
proof for the same project/media and seven unchanged authoring/render modules.
That reuse is not a fresh GUI run of the unchanged upstream `packaging.py` helper.
Raw traces, native artifacts, comparison receipts and individual module hash
manifests were not supplied to the publication environment. Their recorded hashes
and equivalence statements are source-author reports and were not independently
verified here. No artwork, media, new license grant or optional DCT/nlmeans filter
is included.

The accepted render range is frames 0 through 431. The reported proof does not
claim an extra playable frame 432, cross-environment typography, continuous
frame-by-frame GUI playback or XML identity after the editor adds audio filters.
The existing CI native-protocol jobs test bridge behavior, and its render job
tests the existing color-render scenario. They do not qualify this PNG feature
through a Kdenlive editor GUI or a native `qimage` render.
