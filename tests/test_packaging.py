"""Portable bundle safety and exact-byte contract tests."""

import errno
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from dcc_mcp_kdenlive import packaging
from dcc_mcp_kdenlive.project import (
    Project,
    add_media,
    create_project,
    insert_clip,
    properties,
    put,
)
from dcc_mcp_kdenlive.storage import xml_bytes


def make_project(tmp_path, media):
    path = tmp_path / "base.kdenlive"
    create_project(str(path), width=320, height=180, video_tracks=1, audio_tracks=0)
    for i, source in enumerate(media):
        added = tmp_path / ("media-%d.kdenlive" % i)
        result = add_media(str(path), str(added), str(source), 2)
        path = tmp_path / ("cut-%d.kdenlive" % i)
        insert_clip(str(added), str(path), "track_0_0", result["producer_id"], i * 2, 0, 1)
    return path


def media_file(path, data=b"example media"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def native_symlink(link, target, target_is_directory=False):
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except OSError as exc:
        if os.name == "nt" and (
            getattr(exc, "winerror", None) == 1314 or exc.errno in (errno.EPERM, errno.EACCES)
        ):
            pytest.skip("This Windows test process cannot create native symlinks")
        raise


def test_same_basename_and_relative_portability(tmp_path):
    a = media_file(tmp_path / "a/frame.png", b"a")
    b = media_file(tmp_path / "b/frame.png", b"b")
    source = make_project(tmp_path, [a, b])
    out = tmp_path / "portable"
    result = packaging.package_project(str(source), str(out), [str(tmp_path)])
    assert result["media_files"] == 2
    manifest = json.loads((out / "manifest.json").read_text())
    assert {p.read_bytes() for p in (out / "media").iterdir()} == {b"a", b"b"}
    text = (out / "project.kdenlive").read_text() + (out / "manifest.json").read_text()
    assert str(tmp_path) not in text
    assert Project(str(out / "project.kdenlive")).root.get("root") == "."
    assert all(not Path(x["path"]).is_absolute() for x in manifest["files"])


def test_duplicate_content_deduplicates(tmp_path):
    a = media_file(tmp_path / "a.png", b"same")
    b = media_file(tmp_path / "b.png", b"same")
    source = make_project(tmp_path, [a, b])
    result = packaging.package_project(str(source), str(tmp_path / "out"), [str(tmp_path)])
    assert result["media_files"] == 1


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory permissions")
@pytest.mark.parametrize("mask", [0o022, 0o007, 0o077])
def test_published_directory_respects_creation_umask(tmp_path, mask):
    media = media_file(tmp_path / "frame.png")
    source = make_project(tmp_path, [media])
    out = tmp_path / "portable"
    previous = os.umask(mask)
    try:
        packaging.package_project(str(source), str(out), [str(tmp_path)])
        assert stat.S_IMODE(out.stat().st_mode) == 0o777 & ~mask
        assert stat.S_IMODE((out / "media").stat().st_mode) == 0o777 & ~mask
    finally:
        os.umask(previous)


def test_native_avi_exact_bytes_packaged(tmp_path):
    content = b"RIFF" + (16).to_bytes(4, "little") + b"AVI " + b"native-frame-data"
    media = media_file(tmp_path / "native.avi", content)
    source = make_project(tmp_path, [media])
    result = packaging.package_project(str(source), str(tmp_path / "out"), [str(tmp_path)])
    assert result["media_files"] == 1
    assert next((tmp_path / "out/media").iterdir()).read_bytes() == content


@pytest.mark.parametrize(
    "content", [b"", b"RIFF", b"not avi", b"RIFF\x00\x00\x00\x00WAVE", b"RIFF\x00\x00\x00\x00AVIX"]
)
def test_disguised_or_nonprimary_avi_rejected(tmp_path, content):
    media = media_file(tmp_path / "native.avi", content)
    source = make_project(tmp_path, [media])
    with pytest.raises(ValueError, match="RIFF AVI"):
        packaging.package_project(str(source), str(tmp_path / "out"), [str(tmp_path)])
    assert not (tmp_path / "out").exists()


def test_missing_or_outside_media_rejected(tmp_path):
    source_media = media_file(tmp_path / "media/a.png")
    source = make_project(tmp_path, [source_media])
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    with pytest.raises(ValueError):
        packaging.package_project(str(source), str(tmp_path / "out"), [str(allowed)])
    source_media.unlink()
    with pytest.raises(ValueError):
        packaging.package_project(str(source), str(tmp_path / "out"), [str(tmp_path)])
    assert not (tmp_path / "out").exists()


def test_symlink_component_rejected(tmp_path):
    source_media = media_file(tmp_path / "media/a.png")
    source = make_project(tmp_path, [source_media])
    alias = tmp_path / "alias"
    native_symlink(alias, source.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        packaging.package_project(str(alias / source.name), str(tmp_path / "out"), [str(tmp_path)])
    with pytest.raises(ValueError):
        packaging.package_project(str(source), str(tmp_path / "out"), [str(alias)])


def test_existing_destination_preserved(tmp_path):
    source = make_project(tmp_path, [media_file(tmp_path / "a.png")])
    out = tmp_path / "out"
    out.mkdir()
    marker = out / "user-content"
    marker.write_text("keep")
    with pytest.raises(ValueError):
        packaging.package_project(str(source), str(out), [str(tmp_path)])
    assert marker.read_text() == "keep"


def test_concurrent_empty_destination_is_not_replaced(tmp_path, monkeypatch):
    source = make_project(tmp_path, [media_file(tmp_path / "a.png")])
    out = tmp_path / "out"
    original = packaging._publish_directory

    def collide(stage, destination):
        destination.mkdir()
        original(stage, destination)

    monkeypatch.setattr(packaging, "_publish_directory", collide)
    with pytest.raises(FileExistsError):
        packaging.package_project(str(source), str(out), [str(tmp_path)])
    assert out.is_dir() and not list(out.iterdir())
    assert not list(tmp_path.glob(".kdenlive-package-*"))


def test_cancellation_cleans_only_staging(tmp_path, monkeypatch):
    media = media_file(tmp_path / "a.png", b"keep")
    source = make_project(tmp_path, [media])
    calls = [0]

    def cancel():
        calls[0] += 1
        if calls[0] == 3:
            raise RuntimeError("cancelled")

    monkeypatch.setattr(packaging, "check_dcc_cancelled", cancel)
    with pytest.raises(RuntimeError, match="cancelled"):
        packaging.package_project(str(source), str(tmp_path / "out"), [str(tmp_path)])
    assert media.read_bytes() == b"keep"
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".kdenlive-package-*"))


def test_remote_and_residual_private_metadata_rejected(tmp_path):
    source = make_project(tmp_path, [media_file(tmp_path / "a.png")])
    project = Project(str(source))
    producer = next(n for n in project.root if n.tag == "producer" and n.get("id") != "black_track")
    put(producer, "resource", "https://example.com/clip.mp4")
    remote = tmp_path / "remote.kdenlive"
    remote.write_bytes(xml_bytes(project.root))
    with pytest.raises(ValueError):
        packaging.package_project(str(remote), str(tmp_path / "out"), [str(tmp_path)])
    project = Project(str(source))
    put(project.root.find("playlist"), "private_metadata", "/private/source/location")
    private = tmp_path / "private.kdenlive"
    private.write_bytes(xml_bytes(project.root))
    with pytest.raises(ValueError, match="Residual"):
        packaging.package_project(str(private), str(tmp_path / "out"), [str(tmp_path)])


@pytest.mark.parametrize("limit", [True, 0, -1, 2147483649, 2])
def test_byte_budgets(tmp_path, limit):
    source = make_project(tmp_path, [media_file(tmp_path / "a.png", b"longer-than-two")])
    with pytest.raises(ValueError):
        packaging.package_project(
            str(source), str(tmp_path / "out"), [str(tmp_path)], max_total_bytes=limit
        )


def test_revision_conflict(tmp_path):
    source = make_project(tmp_path, [media_file(tmp_path / "a.png")])
    with pytest.raises(ValueError, match="revision"):
        packaging.package_project(
            str(source), str(tmp_path / "out"), [str(tmp_path)], expected_sha256="0" * 64
        )


def alias_project(tmp_path, alias, extra=None):
    source = make_project(tmp_path, [media_file(tmp_path / "media/a.png")])
    project = Project(str(source))
    producer = next(n for n in project.root if n.tag == "producer" and n.get("id") != "black_track")
    put(producer, "kdenlive:originalurl", alias)
    if extra:
        for name, value in extra.items():
            put(producer, name, value)
    result = tmp_path / "alias.kdenlive"
    result.write_bytes(xml_bytes(project.root))
    return result


@pytest.mark.parametrize("relative", [False, True])
def test_originalurl_exact_file_alias_is_packaged(tmp_path, relative):
    alias = "media/../media/a.png" if relative else str(tmp_path / "media/a.png")
    source = alias_project(tmp_path, alias, {"kdenlive:proxy": "-"})
    original = source.read_bytes()
    result = packaging.package_project(
        str(source), str(tmp_path / "out"), [str(tmp_path / "media")]
    )
    project = Project(result["project_path"])
    producer = next(n for n in project.root if n.tag == "producer" and n.get("id") != "black_track")
    prop = properties(producer)
    assert prop["resource"] == prop["kdenlive:originalurl"]
    assert prop["resource"].startswith("media/")
    assert (tmp_path / "out" / prop["resource"]).read_bytes() == b"example media"
    assert str(tmp_path) not in Path(result["project_path"]).read_text()
    assert source.read_bytes() == original


@pytest.mark.parametrize(
    "alias",
    [
        "media/b.png",
        "../outside.png",
        "https://example.com/a.png",
        "file:///tmp/a.png",
        "",
        "media/link.png",
    ],
)
def test_originalurl_dependency_or_remote_alias_rejected(tmp_path, alias):
    media_file(tmp_path / "media/b.png")
    source = alias_project(tmp_path, alias)
    if alias == "media/link.png":
        native_symlink(tmp_path / "media/link.png", tmp_path / "media/a.png")
    with pytest.raises(ValueError):
        packaging.package_project(str(source), str(tmp_path / "out"), [str(tmp_path / "media")])
    assert not (tmp_path / "out").exists()


def test_reparse_component_rejected(tmp_path, monkeypatch):
    component = tmp_path / "redirect"
    component.mkdir()
    original = Path.lstat

    def attributes(path):
        if path == component:
            return SimpleNamespace(st_file_attributes=0x400, st_mode=original(path).st_mode)
        return original(path)

    monkeypatch.setattr(Path, "lstat", attributes)
    with pytest.raises(ValueError, match="reparse"):
        packaging._plain_path(str(component / "new.kdenlive"))


@pytest.mark.parametrize("name", ["resource", "mlt_service", "filename", "file", "lut", "luma"])
def test_duplicate_dependency_properties_rejected(tmp_path, name):
    import xml.etree.ElementTree as ET

    source = alias_project(tmp_path, "media/a.png")
    project = Project(str(source))
    producer = next(n for n in project.root if n.tag == "producer" and n.get("id") != "black_track")
    value = "media/a.png" if name != "mlt_service" else "avformat"
    put(producer, name, value)
    ET.SubElement(producer, "property", name=name).text = value
    source.write_bytes(xml_bytes(project.root))
    with pytest.raises(ValueError, match="Duplicate dependency"):
        packaging.package_project(str(source), str(tmp_path / "out"), [str(tmp_path / "media")])
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".kdenlive-package-*"))
    assert not list(tmp_path.glob(".kdenlive-package-*"))


@pytest.mark.parametrize("proxy", ["proxy", "kdenlive:proxy"])
def test_originalurl_does_not_authorize_proxy(tmp_path, proxy):
    source = alias_project(tmp_path, "media/a.png", {proxy: "media/proxy.png"})
    with pytest.raises(ValueError, match="Proxy"):
        packaging.package_project(str(source), str(tmp_path / "out"), [str(tmp_path / "media")])
    assert not (tmp_path / "out").exists()


def test_duplicate_originalurl_alias_rejected(tmp_path):
    import xml.etree.ElementTree as ET

    source = alias_project(tmp_path, "media/a.png")
    project = Project(str(source))
    producer = next(n for n in project.root if n.tag == "producer" and n.get("id") != "black_track")
    ET.SubElement(producer, "property", name="kdenlive:originalurl").text = "media/other.png"
    source.write_bytes(xml_bytes(project.root))
    with pytest.raises(ValueError, match="Duplicate"):
        packaging.package_project(str(source), str(tmp_path / "out"), [str(tmp_path / "media")])
    assert not (tmp_path / "out").exists()


def test_duplicate_proxy_cannot_hide_a_dependency(tmp_path):
    import xml.etree.ElementTree as ET

    source = alias_project(tmp_path, "media/a.png", {"kdenlive:proxy": "media/proxy.png"})
    project = Project(str(source))
    producer = next(n for n in project.root if n.tag == "producer" and n.get("id") != "black_track")
    ET.SubElement(producer, "property", name="kdenlive:proxy").text = "-"
    source.write_bytes(xml_bytes(project.root))
    with pytest.raises(ValueError, match="Proxy"):
        packaging.package_project(str(source), str(tmp_path / "out"), [str(tmp_path / "media")])
    assert not (tmp_path / "out").exists()
