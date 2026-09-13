# DCC-MCP Kdenlive

Agent tools for Kdenlive project files, installed effects and transitions, media,
subtitles, and MLT rendering. Uses the DCC-MCP Core gateway, skill discovery,
async jobs and shared DCC-CUA editor control.

## Install and run

Install the wheel from GitHub Releases (or `pip install .` from a checkout):

```sh
python -m pip install ./dcc_mcp_kdenlive-0.1.0-py3-none-any.whl
dcc-mcp-kdenlive doctor
dcc-mcp-kdenlive serve
```

The default service is standalone and chooses an available loopback port. It can
edit files independently of the editor. For the existing editor's UI, supply both
its exact PID and native window handle:

```sh
dcc-mcp-kdenlive serve --pid 1234 --hwnd 5678 --host-version 26.08.1
dcc-mcp-cli list
dcc-mcp-cli load-skill kdenlive-project --instance-id INSTANCE_ID
```

Discover the instance through the gateway and use search/describe/call with its
returned tool slugs. The CLI prints its direct MCP URL as an alternative. Configure
an MCP client with that HTTP URL or the machine's DCC-MCP gateway URL.

Configuration:

| Environment variable | Meaning |
| --- | --- |
| `DCC_MCP_KDENLIVE_EXECUTABLE` | Installed Kdenlive executable; also locates sibling MLT/FFmpeg programs |
| `DCC_MCP_KDENLIVE_MELT` | Explicit MLT melt executable |
| `DCC_MCP_KDENLIVE_FFPROBE` | Explicit FFprobe executable |
| `DCC_MCP_KDENLIVE_FFMPEG` | Explicit FFmpeg executable |
| `DCC_MCP_KDENLIVE_DATA` | Installed Kdenlive data directory |
| `DCC_MCP_KDENLIVE_PORT` | Optional fixed instance port |

No editor, plugins or model weights are downloaded implicitly. `doctor` reports
missing programs; install Kdenlive from its official distribution when needed.

## Agent capabilities

Eight progressively loaded skill packages ship in the wheel:

| Skill | Tools |
| --- | --- |
| `kdenlive-project` | Create, inspect, validate and set guides |
| `kdenlive-media` | Import file/color/title producers and relink media |
| `kdenlive-timeline` | Append with gaps, split, remove and ripple |
| `kdenlive-effects` | Add/remove effects, keyframe parameters, compositions |
| `kdenlive-catalog` | Query **installed** MLT services and native asset definitions |
| `kdenlive-export` | Async MP4, WebM, ProRes MOV and WAV rendering |
| `kdenlive-interchange` | FFprobe inspection and SRT subtitle authoring |
| `kdenlive-setup` | Host and executable readiness |

The catalog is dynamic: it exposes the effects/producers/transitions installed
with the host, including their native parameter metadata. It does not assume all
optional MLT plugins are available. Native MLT parameter values, including
keyframe expressions, remain strings; discover each service before configuring it.

Editor-only capabilities (multi-sequence editing, grouped/mixed clips, slip/slide,
multicam, title designer, speech recognition, tracking/rotoscoping, proxies,
recording, layouts and settings) use the existing `ui-control` skill. These are
**UI routes, not claimed native APIs**. They depend on available controls and host
features. See [coverage](docs/capabilities.md) and [live acceptance](docs/acceptance.md).

Every document edit creates a **new file**. Existing outputs are never replaced.
Use the inspection result's `sha256` as `expected_sha256` to fence edits against
stale input. Source files remain unchanged; opening the new artifact and checking
the editor is a separate operation. Grouped and nested timeline mutations reject
with an editor-route instruction. File operations do not participate in editor Undo.

## Render and recover

Load `kdenlive-export`, describe `render_project`, then supply a new output path,
preset, and explicit inclusive `start` / `end` frames. The core returns an async
job ID. Poll `jobs_get_status` until terminal; `jobs_cancel` cooperatively stops
and reaps the render child. The final file is published only after FFprobe finds
streams. The four encoding presets are portable defaults; other native export
configurations remain available through the editor.

## Development and releases

```sh
python -m pip install -e '.[test]' ruff build twine
python -m ruff check src tests tools
python -m ruff format --check src tests tools
python -m pytest -q
python -m build
python -m twine check dist/*
python tools/build_artifacts.py
```

CI validates Linux and Windows, Python 3.7 native compatibility and current Python,
wheel installation, MCP HTTP calls, and real Linux MLT rendering. Release Please
manages versions and changelogs. Release artifacts include wheel, sdist, an agent
skill ZIP, an install manifest and SHA-256 checksums with provenance attestation.
See [release operations](docs/releases.md) for publishing and catalog onboarding.

Kdenlive is a KDE project. This adapter is independently maintained and is not
endorsed by KDE. It does not bundle Kdenlive or MLT binaries.
