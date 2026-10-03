# Single-frame PNG export

`render_project(preset="png", start=N, end=N)` exports one explicit frame through
native MLT as an 8-bit RGBA PNG. Use a new `.png` destination. Dimensions are
limited to 1–4096 on each axis and the nonnegative frame index to 2147483647.
Multi-frame ranges are rejected before starting a renderer.

The async Core job retains the existing staging and non-overwrite publication
behavior. It checks the PNG signature, IHDR CRC, dimensions, encoding fields and
FFprobe stream readback, then checks cancellation again before publication.
These production checks are header/stream checks, not a complete PNG decode.
The qualification below separately decoded the actual output pixels.

## Recorded qualification

The linked [qualification receipt](lossless-png-qualification.json) records the
exact implementation digest and selected MCP requests. Source and installed
wheel suites each passed 141 tests, with the pre-existing opt-in native test
skipped. The public branch also adds a second opt-in native test, so a routine
host-free run has two skips; both native tests passed separately against the
installed wheel.

Source MCP acceptance exported five pairs of explicit samples from a synthetic
four-title fixture, before and after an untouched Kdenlive Save Copy. All ten
PNGs fully decoded and each pair matched in PNG bytes, RGB and RGBA pixels.
Both a multi-frame request and an existing destination were rejected. A second
run imports the installed wheel and extends that comparison to every explicit
content frame; the receipt states its exact coverage.

The separate native CI test constructs 25 red frames followed by 25 blue frames,
exports frame 26, fully decodes it with FFmpeg, and requires exactly one opaque
blue 320×180 image. It also verifies the input project is unchanged. This is
direct adapter/native coverage, separate from the actual SDK/MCP run.

The export manifest generator preserves the PNG preset and documentation
paragraph. Its focused test does not establish whole-generator idempotence.

## Scope

- PNG is lossless encoding. Rendering can still vary with fonts, displays,
  project changes, or other host conditions.
- The same synthetic Save Copy fixture had a failed lossy MP4 comparison.
  Exact PNG results do not erase that result or establish its cause.
- Default editor export-range behavior, production films, and other platforms
  are outside this fixture's scope.
- Cancellation after readback is covered by an injected unit boundary; no new
  live cancellation claim is made.
- This change does not publish a software release.
