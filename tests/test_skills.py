import importlib.util
import json
from pathlib import Path

from dcc_mcp_core import validate_skill

SKILLS = Path(__file__).resolve().parents[1] / "src/dcc_mcp_kdenlive/skills"


def test_skill_validation_and_callable_scripts():
    for directory in SKILLS.iterdir():
        report = validate_skill(str(directory))
        assert not report.has_errors, str(report.issues)
        manifest = json.loads((directory / "tools.yaml").read_text())
        for tool in manifest["tools"]:
            spec = importlib.util.spec_from_file_location(
                tool["name"], directory / tool["source_file"]
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            assert callable(module.main)
