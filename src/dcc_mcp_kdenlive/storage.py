"""Bounded XML and exclusive, copy-on-write artifact publication."""

import hashlib
import io
import os
import tempfile
from pathlib import Path
from xml.etree import ElementTree as StdET

from defusedxml import ElementTree

MAX_XML_BYTES = 32 * 1024 * 1024


def xml_bytes(root):
    stream = io.BytesIO()
    StdET.ElementTree(root).write(stream, encoding="utf-8", xml_declaration=True)
    return stream.getvalue()


def read_xml(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        data = stream.read(MAX_XML_BYTES + 1)
    if len(data) > MAX_XML_BYTES:
        raise ValueError("XML exceeds 32 MiB limit")
    return path, data, ElementTree.fromstring(data)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def publish(path, data):
    """Create a new complete artifact; never replace an existing destination."""
    path = Path(path).absolute()
    if not path.parent.is_dir():
        raise ValueError("Output parent directory must already exist")
    fd, temporary = tempfile.mkstemp(prefix=".kdenlive-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic no-clobber publication, including concurrent callers and symlinks.
        os.link(temporary, str(path))
    finally:
        os.unlink(temporary)
    return {"path": str(path.resolve()), "sha256": digest(data), "bytes": len(data)}
