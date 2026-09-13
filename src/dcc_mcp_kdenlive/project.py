"""Kdenlive/MLT document model. No editor globals or live project writes."""

import copy
import json
import re
import uuid
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from .storage import digest, publish, read_xml


def properties(element):
    return {item.get("name"): item.text or "" for item in element.findall("property")}


def put(element, name, value):
    for child in element.findall("property"):
        if child.get("name") == name:
            child.text = str(value)
            return
    ET.SubElement(element, "property", name=name).text = str(value)


def integer(value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError("Expected an integer >= {}".format(minimum))
    return value


class Project:
    def __init__(self, path, expected_sha256=None):
        self.path, self.original, self.root = read_xml(path)
        if self.root.tag != "mlt" or self.root.find("profile") is None:
            raise ValueError("Expected an MLT document with a profile")
        self.sha256 = digest(self.original)
        if expected_sha256 is not None and expected_sha256 != self.sha256:
            raise ValueError("Source revision conflict; inspect the project again")
        self.validate()

    @property
    def fps(self):
        profile = self.root.find("profile")
        return Fraction(int(profile.get("frame_rate_num")), int(profile.get("frame_rate_den")))

    def frames(self, value):
        if re.fullmatch(r"\d+", str(value)):
            return int(value)
        parts = str(value).split(":")
        if len(parts) != 3:
            raise ValueError("Unsupported MLT time value: {}".format(value))
        seconds = Fraction(parts[0]) * 3600 + Fraction(parts[1]) * 60 + Fraction(parts[2])
        return round(seconds * self.fps)

    def element(self, identifier, tags=None):
        matches = [node for node in self.root.iter() if node.get("id") == identifier]
        if len(matches) != 1 or (tags and matches[0].tag not in tags):
            raise ValueError("Unknown or wrong-kind element: {}".format(identifier))
        return matches[0]

    def fresh_id(self, prefix):
        used = {node.get("id") for node in self.root.iter()}
        index = 0
        while "{}{}".format(prefix, index) in used:
            index += 1
        return "{}{}".format(prefix, index)

    def validate(self):
        if self.fps <= 0:
            raise ValueError("Frame rate must be positive")
        ids = [node.get("id") for node in self.root.iter() if node.get("id")]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate MLT element IDs")
        for node in self.root.iter():
            if node.tag in ("entry", "track") and node.get("producer") not in ids:
                raise ValueError("Dangling producer reference")
            if node.tag == "entry" and self.frames(node.get("out", "0")) < self.frames(
                node.get("in", "0")
            ):
                raise ValueError("Entry ends before it starts")
        return {"valid": True, "elements": len(ids), "fps": str(self.fps)}

    def save(self, output_path):
        self.validate()
        if Path(output_path).resolve() == self.path:
            raise ValueError(
                "Use a new output path; editing an open project in place is prohibited"
            )
        if digest(self.path.read_bytes()) != self.sha256:
            raise ValueError("Source changed during editing")
        # Freeze relative media resolution when the copy moves to another directory.
        root_path = Path(self.root.get("root") or str(self.path.parent))
        if not root_path.is_absolute():
            root_path = self.path.parent / root_path
        self.root.set("root", str(root_path.resolve()))
        result = publish(
            output_path, ET.tostring(self.root, encoding="utf-8", xml_declaration=True)
        )
        result.update(source_sha256=self.sha256, editor_state="file_only")
        return result

    def summary(self):
        elements = []
        for node in self.root:
            if node.get("id"):
                row = {"id": node.get("id"), "type": node.tag, "properties": properties(node)}
                if node.tag == "playlist":
                    row["items"] = self.items(node.get("id"))
                if node.tag == "tractor":
                    row["tracks"] = [dict(track.attrib) for track in node.findall("track")]
                row["effects"] = [
                    dict(effect.attrib, properties=properties(effect))
                    for effect in node.findall("filter")
                ]
                elements.append(row)
        return {
            "path": str(self.path),
            "sha256": self.sha256,
            "profile": dict(self.root.find("profile").attrib),
            "elements": elements,
            "editor_state": "file_only",
        }

    def items(self, playlist_id):
        playlist = self.element(playlist_id, ("playlist",))
        position = 0
        rows = []
        for node in playlist:
            if node.tag not in ("entry", "blank"):
                continue
            length = (
                self.frames(node.get("length"))
                if node.tag == "blank"
                else self.frames(node.get("out")) - self.frames(node.get("in", "0")) + 1
            )
            rows.append(
                {
                    "index": len(rows),
                    "position": position,
                    "duration": length,
                    "type": node.tag,
                    **node.attrib,
                }
            )
            position += length
        return rows

    def editable_playlist(self, identifier):
        playlist = self.element(identifier, ("playlist",))
        if identifier == "main_bin":
            raise ValueError("Use media tools to edit the project bin")
        # Position-indexed groups/mixes require the editor's model to keep them valid.
        for node in self.root.iter("property"):
            if node.get("name", "").endswith("groups") and node.text and json.loads(node.text):
                raise ValueError("Grouped timelines require editor UI control")
        for node in playlist.findall("entry"):
            if self.element(node.get("producer")).tag == "tractor":
                raise ValueError("Nested sequences/mixes require editor UI control")
        return playlist

    def normalize_duration(self):
        # Existing complex documents are preserved; only adapter-created documents
        # have a known sequence graph whose out points can be updated safely.
        if properties(self.element("main_bin", ("playlist",))).get("dcc-mcp:authored") != "1":
            return
        durations = {}
        for playlist in self.root.findall("playlist"):
            if playlist.get("id") != "main_bin":
                durations[playlist.get("id")] = sum(
                    row["duration"] for row in self.items(playlist.get("id"))
                )
        for tractor in self.root.findall("tractor"):
            length = max(
                [durations.get(track.get("producer"), 0) for track in tractor.findall("track")]
                or [0]
            )
            durations[tractor.get("id")] = length
            tractor.set("out", str(max(0, length - 1)))


def create_project(
    output_path, width=1920, height=1080, fps_num=25, fps_den=1, video_tracks=2, audio_tracks=2
):
    for value in (width, height, fps_num, fps_den):
        integer(value, 1)
    integer(video_tracks, 1)
    integer(audio_tracks)
    if video_tracks + audio_tracks > 64:
        raise ValueError("At most 64 tracks")
    aspect = Fraction(width, height)
    root = ET.Element(
        "mlt",
        producer="main_bin",
        version="7.0.0",
        LC_NUMERIC="C",
        root=str(Path(output_path).absolute().parent),
    )
    ET.SubElement(
        root,
        "profile",
        width=str(width),
        height=str(height),
        frame_rate_num=str(fps_num),
        frame_rate_den=str(fps_den),
        progressive="1",
        sample_aspect_num="1",
        sample_aspect_den="1",
        display_aspect_num=str(aspect.numerator),
        display_aspect_den=str(aspect.denominator),
        colorspace="709",
        description="DCC-MCP project",
    )
    main_bin = ET.SubElement(root, "playlist", id="main_bin")
    for name, value in {
        "version": "1.04",
        "documentid": str(uuid.uuid4().int >> 80),
        "audioChannels": "2",
        "zonein": "0",
        "zoneout": "0",
        "groups": "[]",
    }.items():
        put(main_bin, "kdenlive:docproperties." + name, value)
    put(main_bin, "xml_retain", "1")
    put(main_bin, "dcc-mcp:authored", "1")
    black = ET.SubElement(root, "producer", id="black_track", **{"in": "0", "out": "2147483646"})
    for name, value in {
        "mlt_service": "color",
        "resource": "black",
        "length": "2147483647",
        "eof": "continue",
    }.items():
        put(black, name, value)
    for index in range(audio_tracks + video_tracks):
        audio = index < audio_tracks
        for lane in range(2):
            playlist = ET.SubElement(root, "playlist", id="track_{}_{}".format(index, lane))
            if audio:
                put(playlist, "kdenlive:audio_track", "1")
        track = ET.SubElement(
            root, "tractor", id="track_{}".format(index), **{"in": "0", "out": "0"}
        )
        put(
            track,
            "kdenlive:track_name",
            ("A" if audio else "V") + str(index + 1 if audio else index - audio_tracks + 1),
        )
        put(track, "kdenlive:timeline_active", "1")
        if audio:
            put(track, "kdenlive:audio_track", "1")
        for lane in range(2):
            ET.SubElement(
                track,
                "track",
                producer="track_{}_{}".format(index, lane),
                hide="video" if audio else "audio",
            )
    sequence = ET.SubElement(root, "tractor", id="sequence", **{"in": "0", "out": "0"})
    ET.SubElement(sequence, "track", producer="black_track")
    for index in range(audio_tracks + video_tracks):
        ET.SubElement(sequence, "track", producer="track_{}".format(index))
    for index in range(audio_tracks + video_tracks):
        transition = ET.SubElement(sequence, "transition", id="composite_{}".format(index))
        for name, value in {
            "a_track": "0",
            "b_track": str(index + 1),
            "mlt_service": "mix" if index < audio_tracks else "qtblend",
            "internal_added": "237",
            "always_active": "1",
            "sum": "1",
        }.items():
            put(transition, name, value)
    return publish(output_path, ET.tostring(root, encoding="utf-8", xml_declaration=True))


def inspect_project(path):
    return Project(path).summary()


def validate_project(path):
    return Project(path).validate()


def add_media(path, output_path, resource, duration, kind="file", name="", expected_sha256=None):
    integer(duration, 1)
    project = Project(path, expected_sha256)
    if kind not in ("file", "color", "title"):
        raise ValueError("Unsupported producer kind")
    if kind == "file":
        resource = str(Path(resource).resolve(strict=True))
    elif kind == "color" and not re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", resource):
        raise ValueError("Color must be #RRGGBB or #RRGGBBAA")
    elif kind == "title":
        _, _, title = read_xml(resource)
        if title.tag != "kdenlivetitle":
            raise ValueError("Expected a Kdenlive title template")
        resource = ET.tostring(title, encoding="unicode")
    identifier = project.fresh_id("clip_")
    existing_bin_ids = [
        int(properties(node).get("kdenlive:id", "0"))
        for node in project.root
        if properties(node).get("kdenlive:id", "0").isdigit()
    ]
    bin_id = str(max(existing_bin_ids or [0]) + 1)
    producer = ET.Element("producer", id=identifier, **{"in": "0", "out": str(duration - 1)})
    for key, value in {
        "mlt_service": {"file": "avformat", "color": "color", "title": "kdenlivetitle"}[kind],
        "xmldata" if kind == "title" else "resource": resource,
        "length": duration,
        "eof": "pause",
        "kdenlive:id": bin_id,
        "kdenlive:clipname": name or identifier,
    }.items():
        put(producer, key, value)
    project.root.insert(1, producer)
    ET.SubElement(
        project.element("main_bin", ("playlist",)),
        "entry",
        producer=identifier,
        **{"in": "0", "out": str(duration - 1)},
    )
    return dict(project.save(output_path), producer_id=identifier, bin_id=bin_id)


def insert_clip(
    path,
    output_path,
    playlist_id,
    producer_id,
    position,
    source_in,
    source_out,
    expected_sha256=None,
):
    for value in (position, source_in, source_out):
        integer(value)
    if source_out < source_in:
        raise ValueError("Invalid source range")
    project = Project(path, expected_sha256)
    producer = project.element(producer_id, ("producer", "chain"))
    length = properties(producer).get("length")
    if length and source_out >= project.frames(length):
        raise ValueError("Clip exceeds producer duration")
    playlist = project.editable_playlist(playlist_id)
    rows = project.items(playlist_id)
    end = sum(row["duration"] for row in rows)
    if position < end:
        raise ValueError(
            "Insert requires position at or after playlist end; use split/remove first"
        )
    if position > end:
        ET.SubElement(playlist, "blank", length=str(position - end))
    entry = ET.SubElement(
        playlist, "entry", producer=producer_id, **{"in": str(source_in), "out": str(source_out)}
    )
    if properties(producer).get("kdenlive:id"):
        put(entry, "kdenlive:id", properties(producer)["kdenlive:id"])
    project.normalize_duration()
    return project.save(output_path)


def split_clip(path, output_path, playlist_id, item_index, offset, expected_sha256=None):
    integer(item_index)
    integer(offset, 1)
    project = Project(path, expected_sha256)
    playlist = project.editable_playlist(playlist_id)
    items = [node for node in playlist if node.tag in ("entry", "blank")]
    if item_index >= len(items) or items[item_index].tag != "entry":
        raise ValueError("Expected a clip item index")
    entry = items[item_index]
    start, end = project.frames(entry.get("in", "0")), project.frames(entry.get("out"))
    if offset > end - start:
        raise ValueError("Split must be strictly inside the clip")
    second = copy.deepcopy(entry)
    entry.set("out", str(start + offset - 1))
    second.set("in", str(start + offset))
    playlist.insert(list(playlist).index(entry) + 1, second)
    return project.save(output_path)


def remove_item(path, output_path, playlist_id, item_index, ripple=False, expected_sha256=None):
    integer(item_index)
    project = Project(path, expected_sha256)
    playlist = project.editable_playlist(playlist_id)
    items = [node for node in playlist if node.tag in ("entry", "blank")]
    if item_index >= len(items):
        raise ValueError("Unknown item index")
    node = items[item_index]
    if not ripple:
        playlist.insert(
            list(playlist).index(node),
            ET.Element("blank", length=str(project.items(playlist_id)[item_index]["duration"])),
        )
    playlist.remove(node)
    project.normalize_duration()
    return project.save(output_path)


def set_properties(path, output_path, element_id, values, expected_sha256=None):
    project = Project(path, expected_sha256)
    element = project.element(element_id)
    # A typed escape hatch for plugin parameters, not graph/identity rewriting.
    if element.tag not in ("filter", "transition"):
        raise ValueError("Only effect and transition parameters can be changed here")
    reserved = {
        "mlt_service",
        "a_track",
        "b_track",
        "kdenlive:id",
        "kdenlive_id",
        "kdenlive:ix",
        "internal_added",
    }
    for key, value in values.items():
        if not key or key in reserved or not isinstance(value, str):
            raise ValueError("Invalid or structural parameter")
        put(element, key, value)
    return project.save(output_path)


def add_effect(
    path, output_path, element_id, service, parameters, effect_id="", expected_sha256=None
):
    project = Project(path, expected_sha256)
    element = project.element(element_id, ("producer", "chain", "tractor"))
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", service):
        raise ValueError("Invalid MLT service identifier")
    effect = ET.SubElement(element, "filter", id=project.fresh_id("effect_"))
    for key, value in parameters.items():
        if not isinstance(value, str) or key in {
            "mlt_service",
            "kdenlive:id",
            "kdenlive:ix",
            "internal_added",
        }:
            raise ValueError("Invalid effect parameter")
        put(effect, key, value)
    put(effect, "mlt_service", service)
    put(effect, "kdenlive:id", effect_id or service)
    put(effect, "kdenlive:ix", len(element.findall("filter")))
    return dict(project.save(output_path), effect_id=effect.get("id"))


def remove_effect(path, output_path, effect_id, expected_sha256=None):
    project = Project(path, expected_sha256)
    effect = project.element(effect_id, ("filter",))
    if properties(effect).get("internal_added"):
        raise ValueError("Cannot remove internal mixer filters")
    parent = next(node for node in project.root.iter() if effect in list(node))
    parent.remove(effect)
    return project.save(output_path)


def add_transition(
    path,
    output_path,
    tractor_id,
    service,
    a_track,
    b_track,
    start,
    end,
    parameters,
    expected_sha256=None,
):
    for value in (a_track, b_track, start, end):
        integer(value)
    project = Project(path, expected_sha256)
    tractor = project.element(tractor_id, ("tractor",))
    if a_track == b_track or max(a_track, b_track) >= len(tractor.findall("track")) or end < start:
        raise ValueError("Invalid transition tracks or range")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", service):
        raise ValueError("Invalid service")
    transition = ET.SubElement(
        tractor,
        "transition",
        id=project.fresh_id("transition_"),
        **{"in": str(start), "out": str(end)},
    )
    for key, value in parameters.items():
        if key in {
            "mlt_service",
            "a_track",
            "b_track",
            "kdenlive_id",
            "internal_added",
        } or not isinstance(value, str):
            raise ValueError("Invalid transition parameter")
        put(transition, key, value)
    for key, value in {
        "mlt_service": service,
        "a_track": a_track,
        "b_track": b_track,
        "kdenlive_id": service,
    }.items():
        put(transition, key, value)
    return dict(project.save(output_path), transition_id=transition.get("id"))


def relink_media(path, output_path, producer_id, resource, expected_sha256=None):
    project = Project(path, expected_sha256)
    node = project.element(producer_id, ("producer", "chain"))
    if properties(node).get("mlt_service") not in (
        "avformat",
        "avformat-novalidate",
        "qimage",
        "pixbuf",
    ):
        raise ValueError("Producer does not represent file media")
    replacement = str(Path(resource).resolve(strict=True))
    clip_id = properties(node).get("kdenlive:id")
    for producer in project.root:
        if producer is node or (clip_id and properties(producer).get("kdenlive:id") == clip_id):
            put(producer, "resource", replacement)
            put(producer, "kdenlive:originalurl", replacement)
            put(producer, "kdenlive:proxy", "-")
    return project.save(output_path)


def set_guides(path, output_path, guides, expected_sha256=None):
    project = Project(path, expected_sha256)
    normalized = []
    for guide in guides:
        integer(guide["frame"])
        normalized.append(
            {
                "pos": guide["frame"],
                "comment": str(guide["comment"]),
                "type": int(guide.get("category", 0)),
            }
        )
    put(
        project.element("main_bin", ("playlist",)),
        "kdenlive:docproperties.guides",
        json.dumps(normalized),
    )
    return project.save(output_path)
