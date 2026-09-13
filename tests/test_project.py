from xml.etree import ElementTree as ET

import pytest

from dcc_mcp_kdenlive.project import (
    Project,
    add_effect,
    insert_clip,
    properties,
    put,
    remove_effect,
    remove_item,
    set_properties,
    split_clip,
)


def test_roundtrip_and_revision_fence(project, tmp_path):
    source = project.read_bytes()
    document = Project(project)
    output = tmp_path / "split.kdenlive"
    result = split_clip(str(project), str(output), "track_0_0", 0, 10, document.sha256)
    assert project.read_bytes() == source
    assert result["source_sha256"] == document.sha256
    rows = Project(output).items("track_0_0")
    assert [row["duration"] for row in rows] == [10, 15]
    assert rows[1]["in"] == "10"
    with pytest.raises(ValueError, match="revision conflict"):
        split_clip(str(project), str(tmp_path / "bad.kdenlive"), "track_0_0", 0, 10, "0" * 64)


def test_no_clobber_and_atomic_source_guard(project, tmp_path):
    document = Project(project)
    with pytest.raises(ValueError, match="new output"):
        document.save(project)
    target = tmp_path / "existing.kdenlive"
    target.write_text("owned by user")
    with pytest.raises(FileExistsError):
        document.save(target)
    assert target.read_text() == "owned by user"
    project.write_bytes(project.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="changed during"):
        document.save(tmp_path / "conflict.kdenlive")


@pytest.mark.parametrize("ripple,expected", [(False, 25), (True, 0)])
def test_remove_ripple_and_gap(project, tmp_path, ripple, expected):
    result = remove_item(str(project), str(tmp_path / "removed.kdenlive"), "track_0_0", 0, ripple)
    document = Project(result["path"])
    assert sum(row["duration"] for row in document.items("track_0_0")) == expected


def test_effect_parameter_roundtrip(project, tmp_path):
    added = add_effect(
        str(project), str(tmp_path / "fx.kdenlive"), "clip_0", "brightness", {"level": "0=0.5;24=1"}
    )
    updated = set_properties(
        added["path"], str(tmp_path / "updated.kdenlive"), added["effect_id"], {"level": "0.8"}
    )
    assert properties(Project(updated["path"]).element(added["effect_id"]))["level"] == "0.8"
    removed = remove_effect(updated["path"], str(tmp_path / "removed.kdenlive"), added["effect_id"])
    assert not Project(removed["path"]).element("clip_0").findall("filter")


def test_unknown_nodes_preserved(project, tmp_path):
    document = Project(project)
    ET.SubElement(document.root, "future_metadata", value="preserve-me")
    result = document.save(tmp_path / "future.kdenlive")
    added = add_effect(result["path"], str(tmp_path / "fx.kdenlive"), "clip_0", "brightness", {})
    assert Project(added["path"]).root.find("future_metadata").get("value") == "preserve-me"


def test_grouped_edits_fail_closed(project, tmp_path):
    document = Project(project)
    put(document.element("main_bin"), "kdenlive:docproperties.groups", '[{"type":"AVSplit"}]')
    result = document.save(tmp_path / "group.kdenlive")
    with pytest.raises(ValueError, match="Grouped timelines"):
        split_clip(result["path"], str(tmp_path / "no.kdenlive"), "track_0_0", 0, 10)


def test_invalid_bounds_and_references(project, tmp_path):
    with pytest.raises(ValueError, match="duration"):
        insert_clip(str(project), str(tmp_path / "no.kdenlive"), "track_0_0", "clip_0", 25, 0, 30)
    with pytest.raises(ValueError, match="strictly inside"):
        split_clip(str(project), str(tmp_path / "no.kdenlive"), "track_0_0", 0, 25)
    document = Project(project)
    document.element("track_0_0").find("entry").set("producer", "missing")
    with pytest.raises(ValueError, match="Dangling"):
        document.save(tmp_path / "no.kdenlive")


def test_reject_entities(tmp_path):
    path = tmp_path / "entity.kdenlive"
    path.write_text('<!DOCTYPE mlt [<!ENTITY x "expansion">]><mlt>&x;</mlt>')
    with pytest.raises(Exception, match="EntitiesForbidden"):
        Project(path)
