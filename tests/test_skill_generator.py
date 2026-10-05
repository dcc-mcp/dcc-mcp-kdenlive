"""Run schema generation without importing or starting any DCC runtime."""

import ast
import builtins
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {
    "kdenlive-project": {
        "create_project",
        "inspect_project",
        "validate_project",
        "set_guides",
        "package_project",
    },
    "kdenlive-media": {"add_media", "relink_media"},
    "kdenlive-timeline": {"insert_clip", "split_clip", "remove_item"},
    "kdenlive-effects": {"add_effect", "set_properties", "remove_effect", "add_transition"},
    "kdenlive-catalog": {"query_services", "list_assets", "describe_asset"},
    "kdenlive-export": {"render_project"},
    "kdenlive-interchange": {"probe_media", "write_subtitles"},
    "kdenlive-setup": {"get_status"},
    "kdenlive-native": {"handshake", "project_state", "insert_clip", "move_clip", "undo", "redo"},
}


@contextmanager
def host_free():
    """Fail before subprocess, network/listener, native import, or signal actions."""
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {
            "dcc_mcp_kdenlive",
            "dcc_mcp_core",
            "ctypes",
            "psutil",
            "mlt",
            "mlt7",
            "PyQt5",
            "PyQt6",
            "PySide2",
            "PySide6",
        }:
            raise AssertionError("Host-free generation cannot import " + name)
        return original_import(name, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("Host-free generation cannot perform external actions")

    with ExitStack() as stack:
        stack.enter_context(patch.object(builtins, "__import__", guarded_import))
        for module, names in (
            (subprocess, ("Popen", "run", "call", "check_call", "check_output")),
            (socket, ("socket", "socketpair", "create_connection", "getaddrinfo")),
            (
                os,
                (
                    "system",
                    "popen",
                    "fork",
                    "forkpty",
                    "posix_spawn",
                    "posix_spawnp",
                    "spawnl",
                    "spawnle",
                    "spawnlp",
                    "spawnlpe",
                    "spawnv",
                    "spawnve",
                    "spawnvp",
                    "spawnvpe",
                    "execl",
                    "execle",
                    "execlp",
                    "execlpe",
                    "execv",
                    "execve",
                    "execvp",
                    "execvpe",
                    "kill",
                    "killpg",
                    "startfile",
                ),
            ),
        ):
            for name in names:
                if hasattr(module, name):
                    stack.enter_context(patch.object(module, name, forbidden))
        yield


def load_generator(package):
    spec = importlib.util.spec_from_file_location(
        "isolated_skill_generator", ROOT / "tools/generate_skills.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.PACKAGE = package
    return generator


def manifests(package):
    return {
        path.parent.name: json.loads(path.read_text(encoding="utf-8"))["tools"]
        for path in (package / "skills").glob("*/tools.yaml")
    }


def snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


class SkillGeneratorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.package = Path(temporary.name) / "package"
        self.source = ROOT / "src/dcc_mcp_kdenlive"

    def assert_package_contract(self, package):
        generated = next(
            (
                tool
                for tool in manifests(package)["kdenlive-project"]
                if tool["name"] == "package_project"
            ),
            None,
        )
        self.assertIsNotNone(generated, "Generation removed the package_project tool")
        committed = next(
            tool
            for tool in manifests(self.source)["kdenlive-project"]
            if tool["name"] == "package_project"
        )
        self.assertEqual(generated, committed)
        script = package / "skills/kdenlive-project" / generated["source_file"]
        committed_script = self.source / "skills/kdenlive-project" / committed["source_file"]
        # Descriptive docstrings may differ; imports and the kwargs-forwarding
        # entry point must remain identical without executing the packaging code.
        generated_ast = ast.parse(script.read_text(encoding="utf-8"))
        committed_ast = ast.parse(committed_script.read_text(encoding="utf-8"))
        self.assertEqual(
            [ast.dump(node) for node in generated_ast.body[1:]],
            [ast.dump(node) for node in committed_ast.body[1:]],
        )
        skill = (package / "skills/kdenlive-project/SKILL.md").read_text(encoding="utf-8")
        guidance = (
            (self.source / "skills/kdenlive-project/SKILL.md")
            .read_text(encoding="utf-8")
            .split("## Portable native bundles\n\n", 1)[1]
            .strip()
        )
        self.assertIn(guidance, skill)

    def test_regeneration_preserves_all_tools_and_manual_native_files(self):
        shutil.copytree(str(self.source), str(self.package))
        native = snapshot(self.package / "skills/kdenlive-native")
        before = manifests(self.package)
        self.assertEqual(
            {group: {tool["name"] for tool in tools} for group, tools in before.items()},
            EXPECTED_TOOLS,
        )
        self.assertEqual(sum(len(tools) for tools in before.values()), 27)
        with host_free():
            load_generator(self.package).generate()
        after = manifests(self.package)
        self.assertEqual(
            {group: {tool["name"] for tool in tools} for group, tools in after.items()},
            EXPECTED_TOOLS,
        )
        self.assertEqual(sum(len(tools) for tools in after.values()), 27)
        self.assertEqual(snapshot(self.package / "skills/kdenlive-native"), native)
        self.assert_package_contract(self.package)
        for group, tools in after.items():
            for tool in tools:
                self.assertTrue((self.package / "skills" / group / tool["source_file"]).is_file())

    def test_fresh_project_generation_preserves_package_contract(self):
        self.package.mkdir()
        for name in ("project.py", "packaging.py"):
            shutil.copyfile(str(self.source / name), str(self.package / name))
        with host_free():
            generator = load_generator(self.package)
            generator.GROUPS = {"project": generator.GROUPS["project"]}
            generator.generate()
        self.assert_package_contract(self.package)
        self.assertEqual(set(manifests(self.package)), {"kdenlive-project"})

    def test_repeated_generation_is_idempotent(self):
        shutil.copytree(str(self.source), str(self.package))
        with host_free():
            generator = load_generator(self.package)
            generator.generate()
            first = snapshot(self.package)
            generator.generate()
            self.assertEqual(snapshot(self.package), first)
        self.assert_package_contract(self.package)

    def test_guard_blocks_external_actions(self):
        with host_free():
            for action in (
                lambda: subprocess.run(["kdenlive", "--version"]),
                lambda: socket.socket(),
                lambda: socket.create_connection(("localhost", 1)),
                lambda: os.kill(0, 0),
                lambda: __import__("dcc_mcp_kdenlive.packaging"),
                lambda: __import__("ctypes"),
                lambda: __import__("psutil"),
            ):
                with self.assertRaises(AssertionError):
                    action()


if __name__ == "__main__":
    unittest.main()
