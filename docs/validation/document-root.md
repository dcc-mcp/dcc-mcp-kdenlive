# Portable project document root

A packaged project opened in Kdenlive from another working directory can report
missing media when its native root is `.`. Kdenlive 24.12.3's document checker
treats that existing directory as the media base. An empty root instead makes the
checker recover the directory from the opened document URL. Packaged media paths
remain relative and content-addressed; bounded dependency checks and atomic
publication are unchanged.

This contract belongs to Kdenlive's document checker. It is not a claim that
directly invoking raw `melt` on every empty-root document resolves media relative
to that document. The adapter's existing edit, package-input and render paths
already interpret an empty root relative to the source document's parent; the
render path freezes that base before invoking MLT.

The new unit regression actually moves a bundle, makes the original media and
bundle paths unavailable, changes the process working directory, then edits and
repackages the moved project using only its media directory as an allowed root.
It checks byte-exact media and project preservation. This is adapter and structural
coverage; the test does not simulate an editor GUI or decode native media.

## Source-author native qualification

[`document-root-qualification.json`](document-root-qualification.json) preserves
the exact qualification object supplied by the source author. It reports new
cloud checks on merged base `783d2666ccedb944851c48e5e171d3628aa9db1d`, with the
current PNG importer SHA-256
`50edc7d45d55dd3fb6d1e00b4b1a68bd618fa20bcfda612adc580a73556b9fe0`,
and the separate document-root fix's packaging SHA-256
`c5d189886273ea5b9b6b3797b63478797aee5f8df64974a17b9d60424d070bed`.
These are newer reports than the pre-review PNG snapshot, and they are not reuse
of its earlier importer bytes or the earlier 432-frame film proof.

The author reports 109 tests passing with one opt-in live-host skip, fresh typed
MCP authoring/package/render checks, a relocated 24-frame package rendering
byte-identically while its original path is unavailable, and native File Open
from a verified unrelated process working directory without relinking or missing
media. Native Save Copy/reopen, bounded seeks at frames 0/12/23, source preview
and independent same-display comparison of all 24 RGB/RGBA frames and MP4 bytes
were also reported.

The publication environment independently verifies the source packet and source
module hashes, runs local unit/build/archive/fresh-wheel checks, and tracks CI.
Raw native artifacts, MCP traces, GUI receipts and decoder outputs were not
provided to this environment. Their hashes, native results and the source
author's independent comparisons are reported evidence; they were not rerun or
independently decoded here. No local heavy native host or GUI is launched for
this publication.

Native editor coverage is Linux Kdenlive 24.12.3 / MLT 7.30.0 only. No Windows or
macOS editor run, continuous all-frame GUI playback or XML-byte identity after
Save Copy is claimed. The initial unused-black-resource Fixed notice is separate
from missing media and reportedly remains. PNG header preflight does not imply
full decoding, immutable media capture or isolation from hostile parsers. Existing
CI bridge-protocol and color-render tests are separate from these GUI claims.

Source reference: [Kdenlive 24.12.3 DocumentChecker](https://github.com/KDE/kdenlive/blob/v24.12.3/src/doc/documentchecker.cpp#L55).
