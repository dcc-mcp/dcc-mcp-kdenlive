"""Author-time schema generator. Generated files are committed and shipped."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/dcc_mcp_kdenlive"
STR = {"type": "string"}
INT = {"type": "integer", "minimum": 0}
MAP = {"type": "object", "additionalProperties": {"type": "string"}}
SCHEMAS = {
    "values": MAP,
    "parameters": MAP,
    "guides": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"frame": INT, "comment": STR, "category": INT},
            "required": ["frame", "comment"],
            "additionalProperties": False,
        },
    },
    "cues": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"start_ms": INT, "end_ms": INT, "text": STR},
            "required": ["start_ms", "end_ms", "text"],
            "additionalProperties": False,
        },
    },
}
GROUPS = {
    "project": (
        "project",
        {
            "create_project": "Create a Kdenlive project with audio and video tracks.",
            "inspect_project": "Inspect the file profile, bin, tracks, clips and effects; does not read live editor state.",
            "validate_project": "Validate XML references, IDs, frame rate and entry ranges.",
            "set_guides": "Replace project guide markers in a new file.",
        },
    ),
    "media": (
        "project",
        {
            "add_media": "Add file media, a color producer, or a Kdenlive title template to the project bin.",
            "relink_media": "Relink bin media and timeline instances to an existing local media file.",
        },
    ),
    "timeline": (
        "project",
        {
            "insert_clip": "Append a clip at or after the playlist end, inserting a gap when needed.",
            "split_clip": "Split an ungrouped clip at an offset while preserving source ranges.",
            "remove_item": "Remove an ungrouped timeline item, leaving a gap or rippling that playlist.",
        },
    ),
    "effects": (
        "project",
        {
            "add_effect": "Attach an installed MLT audio/video effect to a producer or track. Producer effects affect all its uses.",
            "set_properties": "Update effect or composition parameters, including native MLT keyframe strings.",
            "remove_effect": "Remove a user effect while preserving internal mixer filters.",
            "add_transition": "Add a composition between two tractor tracks for an inclusive frame range.",
        },
    ),
    "catalog": (
        "catalog",
        {
            "query_services": "Discover all installed MLT services or describe one service and its parameters.",
            "list_assets": "List installed Kdenlive effects, transitions, titles, profiles, export presets, generators, lumas or LUTs.",
            "describe_asset": "Read the native parameters from an installed XML asset definition.",
        },
    ),
    "export": (
        "render",
        {
            "render_project": "Render an explicit frame range through MLT to MP4, WebM, ProRes MOV or WAV. Poll core jobs_get_status; use jobs_cancel to cancel."
        },
    ),
    "interchange": (
        "media",
        {
            "probe_media": "Inspect actual audio/video streams and format using FFprobe.",
            "write_subtitles": "Write validated, ordered subtitle cues to a new UTF-8 SRT file for editor import.",
        },
    ),
    "setup": (
        "runtime",
        {
            "get_status": "Report installed renderer tools and running Kdenlive processes without installing or starting the editor."
        },
    ),
}
READ = {
    "get_status",
    "query_services",
    "list_assets",
    "describe_asset",
    "inspect_project",
    "validate_project",
    "probe_media",
}


def generate():
    for group, (module, functions) in GROUPS.items():
        directory = PACKAGE / "skills" / ("kdenlive-" + group)
        (directory / "scripts").mkdir(parents=True, exist_ok=True)
        tree = ast.parse((PACKAGE / (module + ".py")).read_text(encoding="utf-8"))
        definitions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        tools = []
        for name, description in functions.items():
            definition = definitions[name]
            required_count = len(definition.args.args) - len(definition.args.defaults)
            props, required = {}, []
            for index, argument in enumerate(definition.args.args):
                parameter = argument.arg
                default = (
                    ast.literal_eval(definition.args.defaults[index - required_count])
                    if index >= required_count
                    else None
                )
                schema = dict(SCHEMAS.get(parameter, STR))
                if isinstance(default, bool):
                    schema = {"type": "boolean"}
                elif isinstance(default, int) or parameter in {
                    "duration",
                    "position",
                    "source_in",
                    "source_out",
                    "item_index",
                    "offset",
                    "a_track",
                    "b_track",
                    "start",
                    "end",
                }:
                    schema = dict(INT)
                if default is not None:
                    schema["default"] = default
                if parameter == "expected_sha256":
                    schema["pattern"] = "^[0-9a-f]{64}$"
                    schema["description"] = (
                        "Source revision returned by inspect_project. A mismatch rejects the edit."
                    )
                if parameter == "output_path":
                    schema["description"] = (
                        "New file path in an existing directory; existing destinations are never replaced."
                    )
                props[parameter] = schema
                if index < required_count:
                    required.append(parameter)
            # Render ranges are mandatory at the wire boundary, even though the
            # Python function provides defaults for explicit local use.
            if name == "render_project":
                required += ["start", "end"]
            tools.append(
                {
                    "name": name,
                    "description": description,
                    "input_schema": {
                        "type": "object",
                        "properties": props,
                        "required": required,
                        "additionalProperties": False,
                    },
                    "output_schema": {"type": "object"},
                    "source_file": "scripts/" + name + ".py",
                    "execution": "async" if name == "render_project" else "sync",
                    "job_strategy": "monolithic",
                    "affinity": "any",
                    "enforce_thread_affinity": True,
                    "requires_in_process": True,
                    "timeout_hint_secs": 86400 if name == "render_project" else 60,
                    "annotations": {
                        "read_only_hint": name in READ,
                        "destructive_hint": name not in READ,
                        "idempotent_hint": name in READ,
                        "open_world_hint": True,
                        "deferred_hint": name == "render_project",
                    },
                }
            )
            (directory / "scripts" / (name + ".py")).write_text(
                '"""'
                + description
                + '"""\n\nfrom dcc_mcp_kdenlive.'
                + module
                + " import "
                + name
                + "\n\n\ndef main(**kwargs):\n    return "
                + name
                + "(**kwargs)\n",
                encoding="utf-8",
            )
        (directory / "tools.yaml").write_text(
            json.dumps({"tools": tools}, indent=2) + "\n", encoding="utf-8"
        )
        (directory / "SKILL.md").write_text(
            "---\nname: kdenlive-"
            + group
            + "\ndescription: "
            + " ".join(functions.values())
            + '\ncompatibility: "Python 3.7+, dcc-mcp-core 0.20.28+, Kdenlive/MLT installed for native operations"\nmetadata:\n  dcc-mcp:\n    dcc: kdenlive\n    layer: domain\n    version: "0.1.0" # x-release-please-version\n    tools: tools.yaml\n    tags: [kdenlive, video, pipeline]\n    search-hint: "Kdenlive '
            + group
            + " "
            + " ".join(functions)
            + '"\n---\n\n# Kdenlive '
            + group.title()
            + "\n\nDiscover and describe tools before calls. File edits create new artifacts; inspect the returned file before opening it in the editor. Supply expected_sha256 for revision fencing. Frames are integers; end frames are inclusive. File results are not live editor readback.\n\nGrouped clips, nested sequences, timeline model operations and other editor-only features use the shared ui-control skill on a GUI instance bound to an exact Kdenlive PID and HWND. Report provider=dcc-cua and its runtime version before UI observation. Use snapshot -> act -> snapshot and stop the session when done. Never switch to another UI provider or retry after a policy rejection or user interruption.\n\nFor rendering, poll the core job ID until terminal; a timeout is not completion. Cancellation terminates the owned render process and cleans partial output.\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    generate()
