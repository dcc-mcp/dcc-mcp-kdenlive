"""Native PNG still producers retain timing, bytes and publication fences."""

import copy
import json
import os
import struct
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from dcc_mcp_kdenlive.packaging import package_project
from dcc_mcp_kdenlive.project import (
    Project,
    add_media,
    create_project,
    insert_clip,
    properties,
    put,
    relink_media,
)


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


PNG = (
    b"\x89PNG\r\n\x1a\n"
    + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    + png_chunk(b"IDAT", zlib.compress(b"\x00\x40\x80\xc0\xff"))
    + png_chunk(b"IEND", b"")
)


def inputs(tmp_path):
    source = tmp_path / "source.kdenlive"
    create_project(str(source), width=320, height=180, video_tracks=1, audio_tracks=0)
    media = tmp_path / "still.png"
    media.write_bytes(PNG)
    return source, media


def test_native_image_kind_timing_and_portable_bytes(tmp_path):
    source, media = inputs(tmp_path)
    original = source.read_bytes()
    added = add_media(str(source), str(tmp_path / "image.kdenlive"), str(media), 2, kind="image")
    producer = Project(added["path"]).element(added["producer_id"])
    assert properties(producer)["mlt_service"] == "qimage"
    assert properties(producer)["length"] == "2"
    assert producer.attrib["out"] == "1"
    cut = insert_clip(
        added["path"], str(tmp_path / "cut.kdenlive"), "track_0_0", added["producer_id"], 0, 0, 1
    )
    assert Project(cut["path"]).items("track_0_0")[0]["duration"] == 2
    packet = package_project(cut["path"], str(tmp_path / "packet"), [str(tmp_path)])
    exported = Project(packet["project_path"]).element(added["producer_id"])
    assert properties(exported)["mlt_service"] == "qimage"
    assert (Path(packet["directory"]) / properties(exported)["resource"]).read_bytes() == PNG
    assert source.read_bytes() == original
    assert media.read_bytes() == PNG


def test_file_kind_remains_avformat(tmp_path):
    source, media = inputs(tmp_path)
    result = add_media(str(source), str(tmp_path / "file.kdenlive"), str(media), 2)
    assert (
        properties(Project(result["path"]).element(result["producer_id"]))["mlt_service"]
        == "avformat"
    )


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "directory",
        "svg",
        "signature",
        "ihdr",
        "short",
        "oversize",
        "zero_width",
        "zero_height",
        "wide",
        "tall",
        "pixels",
    ],
)
def test_invalid_png_profile_publishes_nothing(tmp_path, case):
    source, media = inputs(tmp_path)
    before = source.read_bytes()
    if case == "missing":
        media.unlink()
    elif case == "directory":
        media.unlink()
        media.mkdir()
    elif case == "svg":
        media = tmp_path / "still.svg"
        media.write_text("<svg/>")
    elif case == "short":
        media.write_bytes(PNG[:20])
    elif case == "oversize":
        with media.open("r+b") as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
    else:
        data = bytearray(PNG)
        if case == "signature":
            data[0] = 0
        elif case == "ihdr":
            data[12:16] = b"IDAT"
        else:
            width, height = {
                "zero_width": (0, 1),
                "zero_height": (1, 0),
                "wide": (8193, 1),
                "tall": (1, 8193),
                "pixels": (4097, 4097),
            }[case]
            data[16:20] = width.to_bytes(4, "big")
            data[20:24] = height.to_bytes(4, "big")
        media.write_bytes(data)
    with pytest.raises((ValueError, FileNotFoundError)):
        add_media(str(source), str(tmp_path / "rejected.kdenlive"), str(media), 2, kind="image")
    assert not (tmp_path / "rejected.kdenlive").exists()
    assert source.read_bytes() == before


def test_image_revision_fence_and_no_overwrite(tmp_path):
    source, media = inputs(tmp_path)
    output = tmp_path / "protected.kdenlive"
    output.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        add_media(str(source), str(output), str(media), 2, kind="image")
    assert output.read_bytes() == b"preserve"
    with pytest.raises(ValueError, match="revision conflict"):
        add_media(
            str(source),
            str(tmp_path / "stale.kdenlive"),
            str(media),
            2,
            kind="image",
            expected_sha256="0" * 64,
        )
    assert not (tmp_path / "stale.kdenlive").exists()


@pytest.mark.parametrize(
    "name",
    [
        "frame-%04d.png",
        "100%.png",
        ".all.png",
        "scene-<svg.png",
        "scene->.png",
        "still?begin=0.png",
    ],
)
def test_existing_valid_png_cannot_expand_native_resource(tmp_path, name):
    if os.name == "nt" and any(character in name for character in "<>?"):
        pytest.skip("Windows forbids creating this filename; no existing local resource can use it")
    source, _ = inputs(tmp_path)
    media = tmp_path / name
    media.write_bytes(PNG)
    before = source.read_bytes()
    with pytest.raises(ValueError, match="QImage"):
        add_media(str(source), str(tmp_path / "rejected.kdenlive"), str(media), 2, kind="image")
    assert not (tmp_path / "rejected.kdenlive").exists()
    assert source.read_bytes() == before
    assert media.read_bytes() == PNG


def test_discovered_schema_explicit_image_kind():
    import dcc_mcp_kdenlive

    root = Path(dcc_mcp_kdenlive.__file__).parent
    schema = json.loads((root / "skills/kdenlive-media/tools.yaml").read_text())["tools"][0][
        "input_schema"
    ]
    assert schema["properties"]["kind"]["enum"] == ["file", "image", "color", "title"]


@pytest.mark.parametrize("name", ["frame-%04d.png", ".all.png"])
def test_qimage_relink_cannot_reintroduce_resource_expansion(tmp_path, name):
    source, media = inputs(tmp_path)
    added = add_media(str(source), str(tmp_path / "image.kdenlive"), str(media), 2, kind="image")
    replacement = tmp_path / name
    replacement.write_bytes(PNG)
    before = Path(added["path"]).read_bytes()
    with pytest.raises(ValueError, match="QImage"):
        relink_media(
            added["path"], str(tmp_path / "bad.kdenlive"), added["producer_id"], str(replacement)
        )
    assert not (tmp_path / "bad.kdenlive").exists()
    assert Path(added["path"]).read_bytes() == before


def test_qimage_relink_keeps_legacy_format_scope(tmp_path):
    source, media = inputs(tmp_path)
    added = add_media(str(source), str(tmp_path / "image.kdenlive"), str(media), 2, kind="image")
    replacement = tmp_path / "replacement.jpg"
    replacement.write_bytes(b"opaque existing native media fixture; decoding is separate")
    result = relink_media(
        added["path"], str(tmp_path / "moved.kdenlive"), added["producer_id"], str(replacement)
    )
    prop = properties(Project(result["path"]).element(added["producer_id"]))
    assert prop["resource"] == str(replacement)
    assert prop["mlt_service"] == "qimage"


def test_relink_other_producer_retains_existing_behavior(tmp_path):
    source, media = inputs(tmp_path)
    added = add_media(str(source), str(tmp_path / "file.kdenlive"), str(media), 2)
    replacement = tmp_path / "literal%.png"
    replacement.write_bytes(PNG)
    result = relink_media(
        added["path"], str(tmp_path / "moved.kdenlive"), added["producer_id"], str(replacement)
    )
    assert (
        properties(Project(result["path"]).element(added["producer_id"]))["mlt_service"]
        == "avformat"
    )


def aliased_qimage_input(tmp_path, same_clip=True):
    source, media = inputs(tmp_path)
    added = add_media(str(source), str(tmp_path / "file.kdenlive"), str(media), 2)
    project = Project(added["path"])
    selected = project.element(added["producer_id"])
    alias = copy.deepcopy(selected)
    alias.tag = "chain"
    alias.set("id", "qimage_alias")
    put(alias, "mlt_service", "qimage")
    if not same_clip:
        put(alias, "kdenlive:id", "unrelated")
    put(alias, "kdenlive:proxy", "old-proxy")
    effect = ET.SubElement(alias, "filter", id="alias_effect")
    put(effect, "mlt_service", "brightness")
    put(effect, "level", "0.5")
    project.root.append(alias)
    result = project.save(str(tmp_path / "aliases.kdenlive"))
    return Path(result["path"]), added["producer_id"]


@pytest.mark.parametrize("name", ["frame-%04d.png", ".all.png"])
def test_qimage_alias_relink_rejects_before_any_publication(tmp_path, name):
    source, producer_id = aliased_qimage_input(tmp_path)
    replacement = tmp_path / name
    replacement.write_bytes(PNG)
    before = source.read_bytes()
    output = tmp_path / "rejected.kdenlive"
    with pytest.raises(ValueError, match="QImage"):
        relink_media(str(source), str(output), producer_id, str(replacement))
    assert source.read_bytes() == before
    assert not output.exists()
    assert replacement.read_bytes() == PNG


def test_safe_relink_updates_all_qimage_aliases_and_preserves_timing_effects(tmp_path):
    source, producer_id = aliased_qimage_input(tmp_path)
    original = Project(str(source))
    before = source.read_bytes()
    replacement = tmp_path / "replacement.png"
    replacement.write_bytes(PNG)
    result = relink_media(
        str(source), str(tmp_path / "moved.kdenlive"), producer_id, str(replacement)
    )
    moved = Project(result["path"])
    for identifier in (producer_id, "qimage_alias"):
        old, new = original.element(identifier), moved.element(identifier)
        assert new.attrib == old.attrib
        assert properties(new)["length"] == properties(old)["length"]
        assert properties(new)["mlt_service"] == properties(old)["mlt_service"]
        assert properties(new)["resource"] == str(replacement.resolve())
        assert properties(new)["kdenlive:originalurl"] == str(replacement.resolve())
        assert properties(new)["kdenlive:proxy"] == "-"
        assert [ET.tostring(item) for item in new.findall("filter")] == [
            ET.tostring(item) for item in old.findall("filter")
        ]
    assert source.read_bytes() == before


def test_unrelated_qimage_does_not_restrict_avformat_relink(tmp_path):
    source, producer_id = aliased_qimage_input(tmp_path, same_clip=False)
    untouched = ET.tostring(Project(str(source)).element("qimage_alias"))
    replacement = tmp_path / "literal%.png"
    replacement.write_bytes(PNG)
    result = relink_media(
        str(source), str(tmp_path / "moved.kdenlive"), producer_id, str(replacement)
    )
    project = Project(result["path"])
    assert properties(project.element(producer_id))["resource"] == str(replacement.resolve())
    assert ET.tostring(project.element("qimage_alias")) == untouched


@pytest.mark.parametrize("parent_name", ["frames%04d", ".all.frames"])
def test_canonical_parent_resource_markers_are_rejected(tmp_path, parent_name):
    source, _ = inputs(tmp_path)
    parent = tmp_path / parent_name
    parent.mkdir()
    media = parent / "still.png"
    media.write_bytes(PNG)
    before = source.read_bytes()
    output = tmp_path / "rejected.kdenlive"
    with pytest.raises(ValueError, match="QImage"):
        add_media(str(source), str(output), str(media), 2, kind="image")
    assert not output.exists()
    assert source.read_bytes() == before
    assert media.read_bytes() == PNG


def test_symlink_marker_is_normalized_to_safe_literal_resource(tmp_path):
    source, media = inputs(tmp_path)
    link = tmp_path / "frame-%04d.png"
    try:
        link.symlink_to(media)
    except OSError as error:
        pytest.skip("Host does not permit creating a real file symlink: {}".format(error))
    result = add_media(str(source), str(tmp_path / "image.kdenlive"), str(link), 2, kind="image")
    prop = properties(Project(result["path"]).element(result["producer_id"]))
    assert prop["resource"] == str(media.resolve())
    assert prop["mlt_service"] == "qimage"
    assert media.read_bytes() == PNG


def test_png_replaced_before_open_cannot_bypass_opened_file_size_bound(tmp_path, monkeypatch):
    source, media = inputs(tmp_path)
    before = source.read_bytes()
    replacement = tmp_path / "oversized.png"
    with replacement.open("wb") as stream:
        stream.write(PNG)
        stream.truncate(64 * 1024 * 1024 + 1)
    original_open = Path.open
    swapped = False

    def replace_then_open(path, *args, **kwargs):
        nonlocal swapped
        if path == media and args == ("rb",) and not swapped:
            os.replace(str(replacement), str(media))
            swapped = True
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", replace_then_open)
    output = tmp_path / "rejected.kdenlive"
    with pytest.raises(ValueError, match="33 bytes and 64 MiB"):
        add_media(str(source), str(output), str(media), 2, kind="image")
    assert swapped
    assert media.stat().st_size == 64 * 1024 * 1024 + 1
    assert source.read_bytes() == before
    assert not output.exists()
