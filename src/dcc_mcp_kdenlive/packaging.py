"""Portable task-owned Kdenlive bundles with bounded, staged no-clobber publication."""

import ctypes
import errno
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path

from dcc_mcp_core.skills_helper import check_dcc_cancelled

from .project import Project, properties, put
from .storage import xml_bytes

_MEDIA_SERVICES = {"avformat", "avformat-novalidate", "qimage", "pixbuf"}
_FILTERS = {"dynamictext", "brightness", "affine", "volume", "panner", "loudness", "audiolevel"}
_TRANSITIONS = {"qtblend", "mix", "luma", "composite", "affine"}
_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".avif",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".exr",
    ".mp4",
    ".mov",
    ".webm",
    ".mkv",
    ".avi",
    ".wav",
    ".mp3",
    ".ogg",
    ".flac",
    ".m4a",
}


def _plain_path(value):
    if not isinstance(value, str) or not value or "\x00" in value or "://" in value:
        raise ValueError("Expected a local filesystem path, never a remote resource")
    path = Path(os.path.abspath(value))
    for component in reversed([path] + list(path.parents)):
        try:
            attributes = getattr(component.lstat(), "st_file_attributes", 0)
        except FileNotFoundError:
            attributes = 0
        if component.is_symlink() or attributes & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
        ):
            raise ValueError("Symlinks and reparse points are not supported in package paths")
    return path


def _inside(path, roots):
    return any(path == root or root in path.parents for root in roots)


def _local_media_path(resource, root_path):
    if not resource or ":" in resource and not re.match(r"^[A-Za-z]:[\\/]", resource):
        raise ValueError("Only explicit local file media can be packaged")
    candidate = Path(resource)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    return _plain_path(str(candidate))


def _copy_checked(source, destination, expected_size):
    if source.suffix.lower() == ".avi" and expected_size < 12:
        raise ValueError("AVI media must have a native RIFF AVI header")
    before = source.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size != expected_size:
        raise ValueError("Only unchanged regular media files can be packaged")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(source), flags)
    digest = hashlib.sha256()
    count = 0
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino, opened.st_size) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ):
            raise ValueError("Media changed before copy")
        incoming = os.fdopen(fd, "rb")
        fd = None
        with incoming, destination.open("xb") as outgoing:
            while True:
                check_dcc_cancelled()
                chunk = incoming.read(1024 * 1024)
                if not chunk:
                    break
                if count == 0 and source.suffix.lower() == ".avi":
                    if len(chunk) < 12 or chunk[:4] != b"RIFF" or chunk[8:12] != b"AVI ":
                        raise ValueError("AVI media must have a native RIFF AVI header")
                count += len(chunk)
                if count > expected_size:
                    raise ValueError("Media grew during copy")
                digest.update(chunk)
                outgoing.write(chunk)
            outgoing.flush()
            os.fsync(outgoing.fileno())
            after_open = os.fstat(incoming.fileno())
        after = source.stat()
        _plain_path(str(source))

        def fields(s):
            return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns

        if (
            count != expected_size
            or fields(before) != fields(after)
            or fields(before) != fields(after_open)
        ):
            raise ValueError("Media changed during copy")
    finally:
        if fd is not None:
            os.close(fd)
    return digest.hexdigest(), count


def _digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            check_dcc_cancelled()
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _publish_directory(source, destination):
    """Atomic rename that cannot replace a concurrent destination, or fail closed."""
    if os.name == "nt":
        os.rename(str(source), str(destination))
        return
    library = ctypes.CDLL(None, use_errno=True)
    rename = getattr(library, "renameat2", None)
    if rename is None:
        raise RuntimeError(
            "Atomic no-replace directory publication is unavailable on this platform"
        )
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(str(source)), -100, os.fsencode(str(destination)), 1) != 0:
        error = ctypes.get_errno()
        if error in (errno.EEXIST, errno.ENOTEMPTY):
            raise FileExistsError("Package destination already exists")
        raise OSError(error, os.strerror(error))


def package_project(
    path, output_directory, allowed_media_roots, max_total_bytes=536870912, expected_sha256=None
):
    """Package explicit file/color media; reject unsupported indirect dependencies.

    Caller-supplied roots describe the media already authorized for this task;
    naming a root is not a grant of authorization. This is a controlled-workspace
    copier, not a sandbox against hostile native parsers or concurrent directory
    attacks. Unknown producers, external title assets and path-bearing effects
    fail rather than silently creating an incomplete archive.
    """
    source = _plain_path(path)
    destination = _plain_path(output_directory)
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError("Select a new destination in an existing directory")
    if type(max_total_bytes) is not int or not 1 <= max_total_bytes <= 2_147_483_648:
        raise ValueError("max_total_bytes must be an integer from 1 to 2 GiB")
    if not isinstance(allowed_media_roots, list) or not 1 <= len(allowed_media_roots) <= 16:
        raise ValueError("Supply 1–16 explicit task-authorized media roots")
    roots = [_plain_path(item) for item in allowed_media_roots]
    if any(not root.is_dir() for root in roots):
        raise ValueError("Every allowed media root must be an existing directory")
    project = Project(str(source), expected_sha256)
    root_path = Path(project.root.get("root") or str(source.parent))
    if not root_path.is_absolute():
        root_path = source.parent / root_path
    root_path = _plain_path(str(root_path))
    dependencies = []
    for node in project.root.iter():
        dependency_names = [
            item.get("name", "").lower()
            for item in node.findall("property")
            if item.get("name", "").lower()
            in {"resource", "mlt_service", "filename", "file", "lut", "luma"}
        ]
        if len(dependency_names) != len(set(dependency_names)):
            raise ValueError("Duplicate dependency properties are not supported")
        prop = properties(node)
        service = prop.get("mlt_service", "")
        if node.tag in ("producer", "chain"):
            if service == "color":
                if (
                    prop.get("resource") not in {"black", "white", "transparent"}
                    and re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", prop.get("resource", ""))
                    is None
                ):
                    raise ValueError("Unsupported color resource")
            elif service in _MEDIA_SERVICES:
                resource = prop.get("resource", "")
                candidate = _local_media_path(resource, root_path)
                if not _inside(candidate, roots) or not candidate.is_file():
                    raise ValueError("Media is missing or outside the task-authorized roots")
                if candidate.suffix.lower() not in _EXTENSIONS:
                    raise ValueError(
                        "Unsupported media extension; indirect dependencies are not packaged"
                    )
                # relink_media writes originalurl as an editable alias. Support
                # only the exact same authorized file, never a second dependency.
                aliases = node.findall("property[@name='kdenlive:originalurl']")
                if len(aliases) > 1:
                    raise ValueError("Duplicate originalurl aliases are not supported")
                if aliases and _local_media_path(aliases[0].text, root_path) != candidate:
                    raise ValueError("originalurl must resolve to the exact resource file")
                # relink_media uses '-' as Kdenlive's disabled-proxy sentinel.
                if any(
                    item.text not in (None, "", "-")
                    for item in node.findall("property")
                    if item.get("name") in ("kdenlive:proxy", "proxy")
                ):
                    raise ValueError("Proxy media dependencies are not supported")
                dependencies.append((node, candidate, candidate.stat().st_size))
            else:
                raise ValueError("Unsupported producer; package only explicit file/color sources")
        elif node.tag == "filter" and service and service not in _FILTERS:
            raise ValueError("Unsupported effect; its external dependencies have not been audited")
        elif node.tag == "transition" and service and service not in _TRANSITIONS:
            raise ValueError("Unsupported transition; its dependencies have not been audited")
        if node.tag not in ("producer", "chain") and any(
            name.lower() in {"resource", "filename", "file", "lut", "luma"} and value
            for name, value in prop.items()
        ):
            raise ValueError(
                "External effect/transition resource is outside the supported packet contract"
            )
    unique = {item[1]: item[2] for item in dependencies}
    if len(unique) > 2048 or sum(unique.values()) > max_total_bytes:
        raise ValueError("Referenced media exceeds the package count/byte budget")
    stage = Path(tempfile.mkdtemp(prefix=".kdenlive-package-", dir=str(destination.parent)))
    try:
        media = stage / "media"
        media.mkdir()
        records = []
        relative = {}
        content_files = {}
        for index, (candidate, size) in enumerate(unique.items()):
            check_dcc_cancelled()
            temporary = media / ("copy-" + str(index))
            digest, count = _copy_checked(candidate, temporary, size)
            name = digest + candidate.suffix.lower()
            target = media / name
            if name in content_files:
                temporary.unlink()
            else:
                temporary.rename(target)
                content_files[name] = target
                records.append({"path": "media/" + name, "bytes": count, "sha256": digest})
            relative[candidate] = "media/" + name
        for node, candidate, _size in dependencies:
            put(node, "resource", relative[candidate])
            if node.find("property[@name='kdenlive:originalurl']") is not None:
                put(node, "kdenlive:originalurl", relative[candidate])
        # An empty root lets Kdenlive recover the directory from the document
        # URL. A literal dot instead selects the editor's launch directory.
        project.root.set("root", "")
        # Kdenlive saves the last project-bin browser location in main_bin.
        # This is editor UI state, not a media dependency or authored content.
        # Omit only this known property; do not generalize to a path scrubber.
        omitted_metadata = []
        for playlist in project.root.findall("playlist[@id='main_bin']"):
            browser = playlist.findall("property[@name='kdenlive:docproperties.browserurl']")
            if len(browser) > 1:
                raise ValueError("Duplicate project-bin browser metadata is not supported")
            if browser:
                if list(browser[0]) or set(browser[0].attrib) != {"name"}:
                    raise ValueError("Only scalar project-bin browser metadata is supported")
                playlist.remove(browser[0])
                omitted_metadata.append("kdenlive:docproperties.browserurl")
        # Reject residual absolute paths or remote resources; do not guess how
        # to redact unknown metadata or silently discard editable content.
        for node in project.root.iter():
            strings = list(node.attrib.values()) + (
                [node.text.strip()] if node.text and node.text.strip() else []
            )
            for text in strings:
                if text.startswith(("/", "\\\\", "file:", "http:", "https:")) or re.match(
                    r"^[A-Za-z]:[\\/]", text
                ):
                    raise ValueError(
                        "Residual private/remote path in project metadata requires explicit support"
                    )
        data = xml_bytes(project.root)
        native = stage / "project.kdenlive"
        native.write_bytes(data)
        records.insert(
            0, {"path": native.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )
        validation = Project(str(native)).validate()
        for item in records:
            actual = stage / item["path"]
            if actual.stat().st_size != item["bytes"] or _digest_file(actual) != item["sha256"]:
                raise RuntimeError("Staged package hash verification failed")
        manifest = {
            "schema_version": 1,
            "kind": "portable-kdenlive-project",
            "source_project_sha256": project.sha256,
            "files": records,
            "media_files": len(records) - 1,
            "media_bytes": sum(item["bytes"] for item in records[1:]),
            "source_dependency_paths_disclosed": False,
            "omitted_editor_metadata": omitted_metadata,
            "metadata_privacy": "Only documented browser UI metadata is omitted; other editor/user metadata is preserved and requires review before sharing.",
            "native_structure_validation": validation,
            "scope": "File/color sources and explicitly supported effects. Native editor reopen and render are separate acceptance.",
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        check_dcc_cancelled()
        _plain_path(str(destination))
        if os.name != "nt":
            # Retain private staging until publication, then use the normal
            # child-directory mode without changing the process-wide umask.
            stage.chmod(stat.S_IMODE(media.stat().st_mode))
        _publish_directory(stage, destination)
        stage = None
        return {
            "directory": str(destination),
            "project_path": str(destination / "project.kdenlive"),
            "manifest_path": str(destination / "manifest.json"),
            "media_files": manifest["media_files"],
            "media_bytes": manifest["media_bytes"],
            "source_dependency_paths_disclosed": False,
            "omitted_editor_metadata": omitted_metadata,
        }
    finally:
        if stage is not None:
            shutil.rmtree(stage)
