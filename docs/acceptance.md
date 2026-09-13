# Acceptance and evidence

## Automated

`python -m pytest` tests copy-on-write isolation, revision conflicts, XML safety,
timeline frame arithmetic, effects, subprocess cancellation, metadata validation
and actual MCP initialize/load/call/error responses. Server tests disable gateway
failover so they cannot disturb a running gateway.

Set `KDENLIVE_LIVE_TEST=1` and configure the MLT/FFprobe executable paths to include
the real renderer test. It creates a project with a color clip, renders a second
of video, and verifies duration and resolution from the final media stream.

## Editor acceptance

1. Start or select Kdenlive and record its version, PID and HWND.
2. Start the adapter with the exact host binding. Discover its live instance.
3. Load `ui-control`; report `provider=dcc-cua runtime=VERSION pid=PID hwnd=HWND`.
4. Snapshot the editor. Preserve any unsaved user project.
5. Open only a test artifact created in a disposable output directory.
6. Re-observe and check the bin, tracks, duration and project monitor. Save a new
   native roundtrip file, then inspect it independently through the project tools.
7. Close the test project, stop UI control and stop the adapter. Confirm its
   registry row is no longer routable.

Every UI action uses a fresh observation. Stop after user interruption or a
permission/policy rejection. No generic Computer Use or alternate input backend
is part of this adapter's acceptance path.

Publication evidence must distinguish unit/MCP tests, renderer acceptance,
editor readback, CI at the exact release SHA, and downloaded release assets.

## 2026-09-13 acceptance

- Native Kdenlive 26.08.1 on Windows opened an adapter-created 640x360 project.
  DCC-CUA 1.8.3 exact-window pixels and UIA confirmed the named bin clip, V1 track,
  two-second duration and matching blue project-monitor image. Native save/reopen
  roundtrip was not established by this observation.
- CLI discovery and progressive skill loading reached a GUI-bound adapter using
  Core 0.20.28. `render_project --wait` traversed pending -> running -> completed.
  FFprobe confirmed H.264, 640x360, 25 fps and 50 video frames in the final artifact.
- The pre-existing unsaved user project was preserved in its original process;
  the acceptance project ran in a separate editor instance.
