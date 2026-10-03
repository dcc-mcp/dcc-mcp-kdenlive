# Portable project publication validation

The source handoff's AVI extension passed 64 tests with one existing installed-host test skipped on Core 0.20.41. It copied a 49,121,546-byte native RIFF AVI exactly and reproduced all 673 decoded MLT frames after relocation with original media/package locations unavailable. The [AVI qualification snapshot](kdenlive-avi-qualification.json) identifies the exact tested packaging source. The RIFF/AVI header check establishes the supported primary-container signature; native probing and rendering establish the separate media acceptance.

Publication review adds rejection of reparse-point paths and duplicate dependency properties, and narrows the metadata privacy field. A fresh Windows Python 3.12 / Core 0.20.41 run passed 69 tests; three tests skipped because MLT is not installed or this Windows process cannot create native symlinks. The non-symlink alias guards and deterministic reparse guard ran. Ruff lint/format, source distribution and wheel builds, and Twine checks passed.

The native snapshots above precede the publication review changes. Exact-head remote CI must still pass, including Linux native rendering and Windows/Python 3.7 compatibility. Native editor GUI acceptance is separate. The package preserves editor/user metadata; review that metadata and the complete package before sharing it.
