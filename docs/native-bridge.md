# Native editor bridge (experimental source integration)

The bridge calls Kdenlive's native C++ model from its GUI thread. It is compiled
into a pinned host; it is **not a DLL that can be dropped into stock Kdenlive**.
The Python adapter retains core MCP discovery, lifecycle and tool execution.
No GUI input or arbitrary code evaluation is involved in the bridge protocol.

## Current coverage and evidence boundaries

Protocol 1 implements handshake, live timeline state, insert an existing bin
clip, move a timeline clip, and undo/redo. It does not yet expose native import,
save, subtitles, effect stacks, keyframes, audio mixing or rendering jobs.
Those remain explicit next integration steps, not advertised native capabilities.

CI builds and tests the real Qt TCP transport on Windows and Linux, tests the
Python client/MCP skill, and applies the overlay to the exact upstream commit.
These checks do **not** compile or validate the full Kdenlive backend. The source
manifest deliberately says `host_binary_verified: false`. A native binary must
not enter releases until full-host compilation and the live acceptance below pass.

The existing file-authoring and MLT rendering tools remain independently usable.

## Reproducible source preparation

`native/upstream.json` pins Kdenlive 26.08.1 at
`55e16e85cd9a9c6e032cd27a621137b4da881a7c`. Start from a clean checkout:

```sh
git clone --depth 1 --branch v26.08.1 https://github.com/KDE/kdenlive.git kdenlive-src
python tools/prepare_native_host.py kdenlive-src
```

The tool refuses a different commit or dirty checkout. Follow upstream's KDE
Craft build instructions and dependency recipes to build the prepared source.
This version requires Qt >=6.10, KDE Frameworks >=6.21, MLT >=7.38,
KDDockWidgets, FFmpeg, OpenTimelineIO and the other upstream CMake dependencies.
The integration adds Qt Network and two translation units to `kdenliveLib`.
Do not copy DLLs from an unrelated Qt toolchain into the installed editor.

Transport-only development:

```sh
cmake -S native -B build/native -DCMAKE_PREFIX_PATH=/path/to/Qt
cmake --build build/native --config Release
ctest --test-dir build/native -C Release --output-on-failure
```

## Launch contract

Launch the bridge-enabled host with operator-owned environment values:

- `DCC_KDENLIVE_BRIDGE_PORT`: an available explicit local TCP port.
- `DCC_KDENLIVE_BRIDGE_TOKEN`: a newly generated random secret, at least 32 characters.

Give the adapter the same values and `DCC_KDENLIVE_BRIDGE_HOST_PID`, then launch
`dcc-mcp-kdenlive serve --pid <exact-pid> --hwnd <exact-hwnd> --host-version 26.08.1`.
Secrets are never tool arguments. The service refuses a bridge PID different
from its bound editor. A normal editor launch without configuration has no listener.
The listener binds IPv4 loopback only, authenticates every request, checks the
expected PID and dispatches on the GUI thread. Modal dialogs return `host_modal`.
One bounded JSON line per connection, protocol version 1, no automatic retry.

Read `handshake` then `project_state`. Native IDs are not XML element IDs.
All mutations require the returned revision; the revision covers active sequence,
project URL, model serialization, undo cursor and a random host session value.
Insertion may also create linked audio; movement follows native grouping rules.
Undo/redo operate on the shared editor undo stack, including human edits.
The response contains a new snapshot. A lost response is an **unknown outcome**:
query fresh state before deciding what to do; never blindly replay the edit.

## Required full-host acceptance before native binary release

1. Build the exact prepared upstream source with its real dependency SDK.
2. Open a disposable project with media and at least one usable track.
3. Start the bound adapter; discover and load `kdenlive-native` through MCP.
4. Handshake and read the actual project; record host/bridge versions and revision.
5. Insert a known bin clip, verify its native ID/position and linked audio.
6. Undo and redo; verify actual model contents after each operation.
7. Make a human edit; demonstrate rejection of the previous revision.
8. Save through the editor, reopen, inspect subtitle/effect/media integrity,
   render and decode the resulting media. Native save API is not implemented yet.
9. Close the host; prove adapter liveness ends and commands fail.

Any visual interaction in this project uses project-owned DCC-CUA with exact
PID/HWND binding. Protocol tests do not substitute for these native checks.

## Distribution

Release packaging includes a deterministic `native-source.zip`, upstream lock,
overlay tool and GPL license, plus SHA256 and existing release provenance.
The adapter Python code remains MIT; native bridge sources are GPL-3.0-or-later.
The combined Kdenlive build must follow Kdenlive's licenses and corresponding
source requirements. No custom Kdenlive executable is shipped in this phase.

Next coverage: native bin import/save, subtitles, effect metadata and typed
parameters, effect stack scopes, keyframes, real overlaps/transitions, audio
envelopes, then render lifecycle. Each capability needs native readback and a
save/reopen check before handshake advertises it.
