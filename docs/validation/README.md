# Validation snapshots

Evidence for the portable `package_project` capability and its AVI media support,
recorded during the work merged as
[PR #9](https://github.com/dcc-mcp/dcc-mcp-kdenlive/pull/9).

> **Point-in-time snapshots.** Each file below freezes one recorded verification run.
> Versions, test counts and frame counts inside them are historical and are kept
> exactly as written: `passed: 46/58/64/69`, `core 0.20.39`, `frames: 660/180/673`
> and similar values describe the run that produced the file, not the current state of
> the repository. Read the `versions` field in each file for its pins, or the
> `validation` block in `portable-package-current-core.json`. To establish current
> status, run the checks again; do not edit these files to refresh their numbers.

## Index

Runs are listed in the order they were performed.

1. **[`portable-package.md`](portable-package.md)** — initial portable-package acceptance against main `fd0a6cc` on Core 0.20.39 / MCP SDK 2.2.0 / Kdenlive 24.12.3: 14 package safety and portability tests, 46 passed with one real-host test skipped, and a five-image, five-track, 660-frame 1280x800 project that keeps every one of its 660 decoded frames identical after relative-path packaging and native MLT re-render.
2. **[`portable-package-live.json`](portable-package-live.json)** — selected actual MCP tool records behind run 1 (`package_project`, two `jobs_get_status` polls, `validate_project`, `render_project`, `probe_media`), pinning `core 0.20.39`, `sdk 2.2.0`, `kdenlive_installed 24.12.3`, `editor_gui_opened: false` and `decoded_video_frames_identical: 660`. The raw trace SHA-256 is retained and the task filesystem prefix is redacted; the full private trace is not published.
3. **[`portable-package-current-core.md`](portable-package-current-core.md)** — the Core 0.20.41 / Kdenlive 24.12.3 / MLT 7.30.0 re-qualification in standalone file mode: 58 passed with one installed-host live test skipped, and a relocated project that re-renders through native MLT with all 180 decoded frames matching while the original media and package directories are unavailable.
4. **[`portable-package-current-core.json`](portable-package-current-core.json)** — the selected actual MCP requests behind run 3, from `search_skills` and four `load_skill` calls through `package_project`, `validate_project`, `render_project` and `probe_media`; carries `validation.status: PASS`, `core`/`server` `0.20.41`, `relocated_decoded_frames_equal: 180`, `sources_restored: true` and the packaging-source and trace digests.
5. **[`kdenlive-avi-qualification.json`](kdenlive-avi-qualification.json)** — the AVI media claims from base `4703e75`, layered on the same packaging source as run 3 (`base_packaging_sha256` equals run 3's `packaging_source_sha256`): a 1280x800 24 fps Godot MovieWriter capture of 699 frames and 49,121,546 bytes copies byte-exactly, and all 673 decoded frames of the relocated MLT re-render match with the original capture and package unavailable; records 64 passed / 1 skipped and both packaging-source digests.
6. **[`portable-package-publication.md`](portable-package-publication.md)** — publication-review coverage of reparse-point and duplicate-dependency rejections, plus three POSIX staging-mode integration cases for umasks 022/007/077 that check restoration of the normal child-directory mode without changing the process-wide umask. The separate Windows Python 3.12 / Core 0.20.41 run reported 69 passed and 6 skipped, including the POSIX mode cases; ruff lint/format, sdist/wheel build and Twine checks passed in that run.

## PNG still image import

[`png-image-import.md`](png-image-import.md) records publication checks for the
explicit native `qimage` PNG kind and its relink guards. Its linked qualification
JSON is clearly labeled source-author reported native evidence; raw traces and
native artifacts were not provided to the publication environment. It is separate
from the six portable-package snapshots above.

## What the six portable-package snapshots do not cover

- No Kdenlive editor GUI acceptance. Every run is standalone file-mode or CLI/SDK work,
  and the earliest packet records `editor_gui_opened: false`.
- No CI result for a release SHA. Remote CI at the exact release commit, and checks on
  downloaded release assets, are separate evidence.
- The 480/576/624-frame round trips mentioned in `portable-package-current-core.md` are
  separate historical packets that are not stored in this directory.
