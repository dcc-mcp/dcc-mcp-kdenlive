import importlib.util
import json
import shutil
from pathlib import Path


def test_export_generator_preserves_png_contract(tmp_path):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "isolated_export_generator", root / "tools/generate_skills.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    package = tmp_path / "package"
    package.mkdir()
    shutil.copyfile(root / "src/dcc_mcp_kdenlive/render.py", package / "render.py")
    generator.PACKAGE = package
    generator.GROUPS = {"export": generator.GROUPS["export"]}
    generator.generate()
    generated = package / "skills/kdenlive-export"
    committed = root / "src/dcc_mcp_kdenlive/skills/kdenlive-export"
    assert json.loads((generated / "tools.yaml").read_text()) == json.loads(
        (committed / "tools.yaml").read_text()
    )
    assert generator.PNG_GUIDANCE in (generated / "SKILL.md").read_text()
    assert generator.PNG_GUIDANCE in (committed / "SKILL.md").read_text()
    assert sorted(x.name for x in (package / "skills").iterdir()) == ["kdenlive-export"]
