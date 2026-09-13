# Install dcc-mcp-kdenlive

This is the agent installation and lifecycle runbook for the Kdenlive adapter.
The adapter is an external Python service. It does not install an editor plugin,
modify Kdenlive startup files, or embed Python in Kdenlive.

## Requirements and supported versions

| Adapter | Core | Host | Python | Platforms |
| --- | --- | --- | --- | --- |
| 0.1.0 | >=0.20.28,<1.0.0 | Kdenlive 26.08.1 verified; installed MLT/FFprobe for rendering | 3.7 and 3.12 tested | Windows and Linux tested; macOS unverified |

Use a dedicated Python environment owned by the adapter. Package installation
writes only that environment. Project tools write new output files in directories
explicitly selected by the caller. Existing files are never overwritten.

Install Kdenlive separately from [the official download page](https://kdenlive.org/download/)
if it is missing. Host installation/startup is a separate user-authorized action;
the package does not download the editor, optional plugins or models.

## Plan and acquire

When the Core release catalog contains this adapter, inspect its install plan:

```sh
dcc-mcp-cli install --dcc-type kdenlive
```

Check the selected interpreter, wheel URL, version and SHA-256 before executing
the Core plan. The plan's presence is not evidence of a live editor instance.

The independently usable manual path is to download the wheel, install manifest
and SHA256SUMS from [v0.1.0](https://github.com/dcc-mcp/dcc-mcp-kdenlive/releases/tag/v0.1.0).
The wheel SHA-256 is:

```text
eb3d1dd71164a00ad44bf2ff7a1e6f58075885df225f99ebb9ee8a8dd00cea2b
```

Verify the downloaded bytes against SHA256SUMS before installation. GitHub CLI
can independently verify the wheel's build provenance:

```sh
gh attestation verify dcc_mcp_kdenlive-0.1.0-py3-none-any.whl --repo dcc-mcp/dcc-mcp-kdenlive
```

## Install and configure

Run these commands with the interpreter selected for the adapter environment:

```sh
python -m pip install ./dcc_mcp_kdenlive-0.1.0-py3-none-any.whl
python -m dcc_mcp_kdenlive.cli --version
python -m dcc_mcp_kdenlive.cli doctor
```

Preserve the install manifest, checksums and pip installation metadata for the
environment. Version 0.1.0 uses Core/pip package acquisition, not an adapter-owned
host installer. It does not expose synthetic `install`, `upgrade`, `status`,
`verify` or `uninstall` CLI verbs or claim an adapter-owned SOP receipt.

Set `DCC_MCP_KDENLIVE_EXECUTABLE` to the exact installed Kdenlive executable.
The adapter locates sibling `melt`, `ffprobe` and `ffmpeg` programs; override them
individually with `DCC_MCP_KDENLIVE_MELT`, `DCC_MCP_KDENLIVE_FFPROBE` and
`DCC_MCP_KDENLIVE_FFMPEG`. Set `DCC_MCP_KDENLIVE_DATA` if asset discovery cannot
find the installation's data directory. No Kdenlive profile edits are required.

## Start and verify usability

For file and render work:

```sh
python -m dcc_mcp_kdenlive.cli serve
```

For an already running editor, supply its independently verified PID and window
handle with `serve --pid PID --hwnd HWND --host-version VERSION`. This binds the
service to that editor's lifetime. It does not attach a native scripting API.

The service prints its MCP URL and instance UUID. In another terminal:

```sh
dcc-mcp-cli list
dcc-mcp-cli search --dcc-type kdenlive --query validate_project
dcc-mcp-cli load-skill kdenlive-project --instance-id INSTANCE_ID
```

Follow the returned describe/call steps. Validate a disposable project file and
check the result independently. For rendering, load `kdenlive-export`, provide a
new output path and explicit frame range, then wait for terminal job completion
and inspect the final streams. `doctor` alone does not prove end-to-end usability.

For UI work, load shared `ui-control` on the GUI-bound instance. Report
`provider=dcc-cua runtime=VERSION pid=PID hwnd=HWND` before the first observation.
Use fresh snapshot -> action -> snapshot and stop UI control when finished.
Readiness/policy/interruption failures are blockers, not permission to switch
providers. Preserve unsaved projects. See [acceptance](docs/acceptance.md).

## Upgrade and rollback

1. Finish or cancel outstanding jobs and stop the adapter process with Ctrl+C.
2. Download and verify the desired release into a new dedicated environment.
3. Run its version, doctor, MCP and render checks before switching the launcher.
4. Keep the previous environment and its verified artifacts until acceptance.

Rollback switches the launcher back to the previous verified environment. Do not
replace imported code underneath a running adapter. The external service can be
restarted independently; it never requires terminating a user-owned editor.

## Uninstall

Stop UI control and the adapter process, then use its selected interpreter:

```sh
python -m pip uninstall dcc-mcp-kdenlive
```

Pip removes files owned by the distribution. Project files, media, render outputs,
Kdenlive settings and other packages remain user-owned. No host startup hooks
need removal. Confirm the old instance is no longer routable with `dcc-mcp-cli list`.

## Troubleshooting

| Symptom | Recovery |
| --- | --- |
| Missing renderer / probe | Set the exact executable paths and rerun doctor |
| Zero live instances | Start the selected environment's service; package installation alone is insufficient |
| Missing PID or HWND | Supply both verified values, or use standalone file mode |
| Existing output / revision conflict | Inspect the current source and choose a new destination |
| Grouped / nested timeline rejected | Use the editor's scoped UI route to preserve model relationships |
| Render pending or transport loss | Query the existing core job ID; do not resubmit blindly |
| UI policy rejection or interruption | Stop that workflow and resolve the reported boundary |
