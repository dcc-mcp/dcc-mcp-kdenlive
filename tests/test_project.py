import os
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


@pytest.fixture(autouse=True)
def native_effect_catalog(tmp_path, monkeypatch):
    """Keep document-model unit tests independent of host installation."""
    data = tmp_path / "effect-catalog"
    effects = data / "effects"
    effects.mkdir(parents=True)
    for native_id, service in [
        ("brightness", "brightness"),
        ("dynamictext", "dynamictext"),
        ("fade_from_black", "brightness"),
    ]:
        (effects / (native_id + ".xml")).write_text(
            '<effect id="{}" tag="{}"/>'.format(native_id, service)
        )
    monkeypatch.setenv("DCC_MCP_KDENLIVE_DATA", str(data))
    return effects


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


@pytest.mark.parametrize("target", ["clip_0", "track_0", "sequence"])
def test_effect_has_native_import_identity(project, tmp_path, target):
    # Kdenlive 24.12 EffectStackModel::importEffects ignores filters without
    # kdenlive_id. kdenlive:id identifies bin clips, not native effects.
    before = project.read_bytes()
    result = add_effect(
        str(project),
        str(tmp_path / "native-fx.kdenlive"),
        target,
        "dynamictext",
        {"argument": "Native caption"},
    )
    effect = Project(result["path"]).element(result["effect_id"])
    assert properties(effect)["kdenlive_id"] == "dynamictext"
    assert "kdenlive:id" not in properties(effect)
    assert properties(effect)["argument"] == "Native caption"
    assert project.read_bytes() == before


def test_explicit_native_effect_id_is_distinct_from_graph_id(project, tmp_path):
    result = add_effect(
        str(project),
        str(tmp_path / "native-fx.kdenlive"),
        "sequence",
        "brightness",
        {"level": "1"},
        effect_id="fade_from_black",
    )
    effect = Project(result["path"]).element(result["effect_id"])
    assert properties(effect)["kdenlive_id"] == "fade_from_black"
    assert properties(effect)["mlt_service"] == "brightness"
    assert effect.get("id") == result["effect_id"]


@pytest.mark.parametrize("key", ["kdenlive_id", "kdenlive:id"])
def test_effect_parameters_cannot_override_native_identity(project, tmp_path, key):
    before = project.read_bytes()
    output = tmp_path / "rejected-identity.kdenlive"
    with pytest.raises(ValueError, match="Invalid effect parameter"):
        add_effect(str(project), str(output), "sequence", "dynamictext", {key: "brightness"})
    assert not output.exists()
    assert project.read_bytes() == before


@pytest.mark.parametrize(
    "native_id,service",
    [("missing_native_effect", "brightness"), ("dynamictext", "brightness")],
)
def test_unknown_or_mismatched_identity_rejected_before_output(
    project, tmp_path, native_id, service
):
    before = project.read_bytes()
    output = tmp_path / "rejected-native.kdenlive"
    with pytest.raises(ValueError, match="Native effect ID"):
        add_effect(str(project), str(output), "sequence", service, {}, effect_id=native_id)
    assert not output.exists()
    assert project.read_bytes() == before


def test_conflicting_installed_identity_rejected(project, tmp_path, native_effect_catalog):
    (native_effect_catalog / "conflict.xml").write_text(
        '<effect id="dynamictext" tag="brightness"/>'
    )
    output = tmp_path / "rejected-conflict.kdenlive"
    with pytest.raises(ValueError, match="uniquely match"):
        add_effect(str(project), str(output), "sequence", "dynamictext", {})
    assert not output.exists()


def test_oversized_installed_definition_rejected(project, tmp_path, native_effect_catalog):
    (native_effect_catalog / "large.xml").write_bytes(b" " * (256 * 1024 + 1))
    output = tmp_path / "rejected-large.kdenlive"
    with pytest.raises(ValueError, match="byte limit"):
        add_effect(str(project), str(output), "sequence", "dynamictext", {})
    assert not output.exists()


def test_unavailable_installed_catalog_rejected(project, tmp_path, monkeypatch):
    monkeypatch.setenv("DCC_MCP_KDENLIVE_DATA", str(tmp_path / "absent"))
    output = tmp_path / "rejected-absent.kdenlive"
    with pytest.raises(FileNotFoundError):
        add_effect(str(project), str(output), "sequence", "dynamictext", {})
    assert not output.exists()


def test_grouped_installed_definition_is_supported(project, tmp_path, native_effect_catalog):
    (native_effect_catalog / "group.xml").write_text(
        '<group><effect id="grouped_brightness" tag="brightness"/></group>'
    )
    result = add_effect(
        str(project),
        str(tmp_path / "grouped.kdenlive"),
        "sequence",
        "brightness",
        {},
        effect_id="grouped_brightness",
    )
    assert (
        properties(Project(result["path"]).element(result["effect_id"]))["kdenlive_id"]
        == "grouped_brightness"
    )


def test_catalog_walk_error_is_not_silently_ignored(project, tmp_path, monkeypatch):
    from dcc_mcp_kdenlive import catalog

    def unreadable_walk(base, followlinks, onerror):
        onerror(PermissionError("catalog subtree unreadable"))
        return iter(())

    monkeypatch.setattr(catalog.os, "walk", unreadable_walk)
    output = tmp_path / "rejected-unreadable.kdenlive"
    with pytest.raises(PermissionError, match="catalog subtree"):
        add_effect(str(project), str(output), "sequence", "dynamictext", {})
    assert not output.exists()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO fixture")
def test_fifo_catalog_definition_rejected_without_opening(
    project, tmp_path, native_effect_catalog, monkeypatch
):
    from dcc_mcp_kdenlive import catalog

    os.mkfifo(str(native_effect_catalog / "000-fifo.xml"))

    def unexpected_open(*args, **kwargs):
        raise AssertionError("FIFO must be rejected before open")

    monkeypatch.setattr(catalog.os, "open", unexpected_open)
    output = tmp_path / "rejected-fifo.kdenlive"
    with pytest.raises(ValueError, match="regular catalog files"):
        add_effect(str(project), str(output), "sequence", "dynamictext", {})
    assert not output.exists()


def test_symlinked_effects_root_rejected(project, tmp_path, native_effect_catalog, monkeypatch):
    from pathlib import Path

    original = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink", lambda path: path == native_effect_catalog or original(path)
    )
    output = tmp_path / "rejected-linked-root.kdenlive"
    with pytest.raises(ValueError, match="must not be a symlink"):
        add_effect(str(project), str(output), "sequence", "dynamictext", {})
    assert not output.exists()


@pytest.mark.parametrize("grouped", [False, True])
def test_kdenlive_namespaced_effect_is_supported(project, tmp_path, native_effect_catalog, grouped):
    effect = '<effect id="dynamictext" tag="dynamictext"/>'
    if grouped:
        xml = '<group xmlns="https://www.kdenlive.org">' + effect + "</group>"
    else:
        xml = '<effect xmlns="https://www.kdenlive.org" id="dynamictext" tag="dynamictext"/>'
    (native_effect_catalog / "dynamictext.xml").write_text(xml)
    result = add_effect(
        str(project), str(tmp_path / "namespaced.kdenlive"), "sequence", "dynamictext", {}
    )
    assert (
        properties(Project(result["path"]).element(result["effect_id"]))["kdenlive_id"]
        == "dynamictext"
    )


def test_namespaced_conflict_with_legacy_definition_rejected(
    project, tmp_path, native_effect_catalog
):
    (native_effect_catalog / "namespace-conflict.xml").write_text(
        '<group xmlns="https://www.kdenlive.org">'
        '<effect id="dynamictext" tag="brightness"/></group>'
    )
    output = tmp_path / "namespace-conflict.kdenlive"
    with pytest.raises(ValueError, match="uniquely match"):
        add_effect(str(project), str(output), "sequence", "dynamictext", {})
    assert not output.exists()


def test_unknown_namespace_does_not_supply_native_identity(
    project, tmp_path, native_effect_catalog
):
    (native_effect_catalog / "dynamictext.xml").write_text(
        '<effect xmlns="urn:other-format" id="dynamictext" tag="dynamictext"/>'
    )
    output = tmp_path / "unknown-namespace.kdenlive"
    with pytest.raises(ValueError, match="not in the installed XML catalog"):
        add_effect(str(project), str(output), "sequence", "dynamictext", {})
    assert not output.exists()
