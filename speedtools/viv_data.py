#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from enum import Enum
from functools import partial
from itertools import compress, starmap
from pathlib import Path
from typing import Any, NamedTuple
from more_itertools.more import groupby_transform

from more_itertools import one

from speedtools.carp_data import CarpData
from speedtools.parsers import FceParser, VivParser, CtbParser
from speedtools.bnk_data import BnkData
from speedtools.types import (
    AudioStream,
    UV,
    Color,
    DrawableMesh,
    EngineAudio,
    EngineAudioType,
    Image,
    Part,
    Polygon,
    Resource,
    ShapeKey,
    ShapeKeyType,
    SoundTable,
    Vector3d,
    VehicleLight,
    VehicleLightType,
    Vertex,
)
from speedtools.utils import islicen

logger = logging.getLogger(__name__)


class Resolution(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class PartAttributes(NamedTuple):
    name: str
    interior: bool = False
    resolution: Resolution = Resolution.HIGH


class VivData:
    known_parts: dict[str, PartAttributes] = {
        # High Body
        ":HB": PartAttributes(resolution=Resolution.HIGH, name="body"),
        # High Left Front Wheel
        ":HLFW": PartAttributes(resolution=Resolution.HIGH, name="front_left_whl"),
        # High Right Front Wheel
        ":HRFW": PartAttributes(resolution=Resolution.HIGH, name="front_right_whl"),
        # High Left Middle Wheel
        ":HLMW": PartAttributes(resolution=Resolution.HIGH, name="middle_left_whl"),
        # High Right Middle Wheel
        ":HRMW": PartAttributes(resolution=Resolution.HIGH, name="middle_right_whl"),
        # High Left Rear Wheel
        ":HLRW": PartAttributes(resolution=Resolution.HIGH, name="rear_left_whl"),
        # High Right Rear Wheel
        ":HRRW": PartAttributes(resolution=Resolution.HIGH, name="rear_right_whl"),
        # Medium Body
        ":MB": PartAttributes(resolution=Resolution.MEDIUM, name="body"),
        # Medium Left Front Wheel
        ":MLFW": PartAttributes(resolution=Resolution.MEDIUM, name="front_left_whl"),
        # Medium Right Front Wheel
        ":MRFW": PartAttributes(resolution=Resolution.MEDIUM, name="front_right_whl"),
        # Medium Left Middle Wheel
        ":MLMW": PartAttributes(resolution=Resolution.MEDIUM, name="middle_left_whl"),
        # Medium Right Middle Wheel
        ":MRMW": PartAttributes(resolution=Resolution.MEDIUM, name="middle_right_whl"),
        # Medium Left Rear Wheel
        ":MLRW": PartAttributes(resolution=Resolution.MEDIUM, name="rear_left_whl"),
        # Medium Right Rear Wheel
        ":MRRW": PartAttributes(resolution=Resolution.MEDIUM, name="rear_right_whl"),
        # Low Body
        ":LB": PartAttributes(resolution=Resolution.LOW, name="body"),
        # Tiny Body
        ":TB": PartAttributes(resolution=Resolution.LOW, name="body"),
        # Interior
        ":OC": PartAttributes(resolution=Resolution.HIGH, name="interior"),
        # Driver's chair and steering wheel
        ":OND": PartAttributes(resolution=Resolution.HIGH, name="driver_chair"),
        # Driver holding steering wheel
        ":OD": PartAttributes(resolution=Resolution.HIGH, name="driver"),
        # Driver head
        ":OH": PartAttributes(resolution=Resolution.HIGH, name="driver_head"),
        # Dash when lit
        ":ODL": PartAttributes(resolution=Resolution.HIGH, name="dashboard_lit"),
        # Left Mirror
        ":OLM": PartAttributes(resolution=Resolution.HIGH, name="left_mirror"),
        # Right Mirror
        ":ORM": PartAttributes(resolution=Resolution.HIGH, name="right_mirror"),
        # Left Front Brake
        ":OLB": PartAttributes(resolution=Resolution.HIGH, name="front_left_brake"),
        # Right Front Brake
        ":ORB": PartAttributes(resolution=Resolution.HIGH, name="front_right_brake"),
        # Popup lights
        ":OL": PartAttributes(resolution=Resolution.HIGH, name="lights"),
        # Top of convertibles
        ":OT": PartAttributes(resolution=Resolution.HIGH, name="top"),
        # Optional spoiler
        ":OS": PartAttributes(resolution=Resolution.HIGH, name="spoiler"),
        # Helicopter main rotor
        "main": PartAttributes(resolution=Resolution.HIGH, name="main_rotor"),
        # Helicopter tail rotor
        "tail": PartAttributes(resolution=Resolution.HIGH, name="tail_rotor"),
        # Helicopter body
        "body": PartAttributes(resolution=Resolution.HIGH, name="body"),
        # Low resolution main rotor
        ":Lmain": PartAttributes(resolution=Resolution.LOW, name="main_rotor"),
        # Low resolution tail rotor
        ":Ltail": PartAttributes(resolution=Resolution.LOW, name="tail_rotor"),
    }

    light_types = {
        "H": VehicleLightType.HEADLIGHT,
        "T": VehicleLightType.TAILLIGHT,
        "B": VehicleLightType.BRAKELIGHT,
        "R": VehicleLightType.REVERSE,
        "P": VehicleLightType.DIRECTIONAL,
        "S": VehicleLightType.SIREN,
    }

    light_colors = {
        "R": Color(0xFF, 0, 0),
        "B": Color(0, 0, 0xFF),
        "W": Color(0xFF, 0xFF, 0xFF),
        "O": Color(0xE4, 0xA4, 0),
        "Y": Color(0xFF, 0xFF, 0),
    }

    body_geometry = {"car.fce", "hel.fce"}
    body_textures = {"car00.tga", "hel00.tga"}
    interior_geometry = {"dash.fce"}
    interior_textures = {"dash00.tga"}
    ltb = "careng.ltb"
    ctb = "careng.ctb"
    bnk = "careng.bnk"

    def __init__(self, parser: VivParser) -> None:
        self.viv = parser

    @classmethod
    def from_file(cls, path: Path) -> VivData:
        parser = VivParser.from_file(path)
        return cls(parser=parser)

    @classmethod
    def _make_polygon(cls, polygon: FceParser.Polygon) -> Polygon:
        face = tuple(vertex for vertex in polygon.face)
        uv = tuple(UV(u, 1 - v) for u, v in zip(polygon.u, polygon.v))
        return Polygon(
            face=face,
            uv=uv,
            material=polygon.texture,
            backface_culling=polygon.backface_culling,
            transparent=polygon.transparent,
            highly_reflective=polygon.highly_reflective,
            non_reflective=polygon.non_reflective,
        )

    @classmethod
    def _match_attributes(cls, attribute: PartAttributes) -> bool:
        return attribute.resolution is Resolution.HIGH

    @classmethod
    def _get_part_attributes(cls, strings: FceParser.Part) -> PartAttributes:
        try:
            return cls.known_parts[strings.value[0]]
        except KeyError:
            return PartAttributes(name=strings.value[0])

    @classmethod
    def _make_vertex(
        cls, vertex: Iterable[FceParser.Float3], normal: Iterable[FceParser.Float3]
    ) -> Vertex:
        location = Vector3d.from_fce_float3(vertex)
        normal_vec = Vector3d.from_fce_float3(normal)
        return Vertex(location=location, normal=normal_vec)

    @classmethod
    def _make_part_shape_key(
        cls, vertices: Iterable[FceParser.Float3], normals: Iterable[FceParser.Float3]
    ) -> ShapeKey:
        vert = list(map(cls._make_vertex, vertices, normals))
        return ShapeKey(type=ShapeKeyType.DAMAGE, vertices=vert)

    @classmethod
    def _make_part_mesh(
        cls,
        part_vertices: Iterable[FceParser.Float3],
        part_normals: Iterable[FceParser.Float3],
        part_polygons: Iterable[FceParser.Polygon],
        part_damaged_vertices: Iterable[FceParser.Float3],
        part_damaged_normals: Iterable[FceParser.Float3],
    ) -> DrawableMesh:
        vertices = list(map(cls._make_vertex, part_vertices, part_normals))
        shape_key = cls._make_part_shape_key(part_damaged_vertices, part_damaged_normals)
        polygons = [cls._make_polygon(polygon) for polygon in part_polygons]
        return DrawableMesh(vertices=vertices, polygons=polygons, shape_keys=[shape_key])

    @classmethod
    def _make_part(
        cls, location: FceParser.Float3, mesh: DrawableMesh, attribute: PartAttributes
    ) -> Part:
        location_vect = Vector3d(x=location.x, y=location.y, z=location.z)
        return Part(name=attribute.name, location=location_vect, mesh=mesh)

    @classmethod
    def _make_resource(cls, entry: VivParser.DirectoryEntry) -> Resource:
        tga = Image(entry.body)
        return Resource(name=entry.name, image=tga)

    @classmethod
    def _make_geometry(cls, fce: FceParser) -> Iterator[Part]:
        slice_vert = partial(islicen, fce.undamaged_vertices)
        part_vertices_iter = map(slice_vert, fce.part_vertex_index, fce.part_num_vertices)
        slice_norm = partial(islicen, fce.undamaged_normals)
        part_normals_iter = map(slice_norm, fce.part_vertex_index, fce.part_num_vertices)
        slice_norm = partial(islicen, fce.polygons)
        part_polygons_iter = map(slice_norm, fce.part_polygon_index, fce.part_num_polygons)
        slice_damaged_vert = partial(islicen, fce.damaged_vertices)
        part_damaged_vertices_iter = map(
            slice_damaged_vert, fce.part_vertex_index, fce.part_num_vertices
        )
        slice_damaged_norm = partial(islicen, fce.damaged_normals)
        part_damaged_normals_iter = map(
            slice_damaged_norm, fce.part_vertex_index, fce.part_num_vertices
        )
        meshes = map(
            cls._make_part_mesh,
            part_vertices_iter,
            part_normals_iter,
            part_polygons_iter,
            part_damaged_vertices_iter,
            part_damaged_normals_iter,
        )
        attributes = list(map(cls._get_part_attributes, fce.part_strings))
        part_data = zip(fce.part_locations, meshes, attributes, strict=True)
        selectors = map(cls._match_attributes, attributes)
        filtered_parts = compress(part_data, selectors)
        return starmap(cls._make_part, filtered_parts)

    @classmethod
    def _make_light(cls, location: FceParser.Float3, dummy: FceParser.Dummy) -> VehicleLight:
        loc = Vector3d.from_fce_float3(location)
        color = cls.light_colors[dummy.color]
        light_type = cls.light_types[dummy.magic]
        logger.debug(f"Color: {color}")
        return VehicleLight(location=loc, color=color, type=light_type)

    def _make_sound_table(
        cls, table_type: EngineAudioType, entry: VivParser.DirectoryEntry
    ) -> Iterable[tuple[int, SoundTable]]:
        table_data = filter(
            lambda x: x[0] != -1, zip(entry.body.patchnum, entry.body.volume, entry.body.pitch)
        )
        return starmap(
            lambda s, v, p: (s, SoundTable(volume=v.value, pitch=p.value, table_type=table_type)),
            table_data,
        )

    # @classmethod
    # def _make_engine_audio(cls, samples: dict[int, AudioStream], patchnum: int, table: SoundTable) -> EngineAudio
    #     attrib = {EngineAudioDirection.FRONT} if patchnum < 0x40 else {EngineAudioDirection.REAR}
    #     return EngineAudio(stream=samples[patchnum], tables=[(attrib, table)])

    @staticmethod
    def merge_tables(
        samples: dict[int, AudioStream],
        load: list[tuple[int, SoundTable]],
        coast: list[tuple[int, SoundTable]],
    ) -> Iterable[EngineAudio]:
        # def mkattr(data: tuple[int, SoundTable]) -> tuple[EngineAudioDirection, SoundTable]:
        #     patchnum, sample = data
        #     direction = EngineAudioDirection.FRONT if patchnum < 0x40 else EngineAudioDirection.REAR
        #     return (patchnum, direction, sample)
        # load_tables = [mkattr(x) for x in load]
        # coast_tables = [mkattr(x) for x in coast]
        load_tables = dict(load)
        coast_tables = dict(coast)
        for identifier, sample in samples.items():
            l = load_tables.get(identifier, None)
            c = coast_tables.get(identifier, None)
            is_rear = identifier > 0x40
            tbl = []
            if l:
                tbl.append(l)
            if c:
                tbl.append(c)
            if not tbl:
                continue
            yield EngineAudio(stream=sample, tables=tbl, is_rear=is_rear)

    @property
    def parts(self) -> Iterator[Part]:
        fce = one(filter(lambda x: x.name in self.body_geometry, self.viv.entries))
        return self._make_geometry(fce.body)

    @property
    def interior(self) -> Iterator[Part]:
        fce = one(filter(lambda x: x.name in self.interior_geometry, self.viv.entries))
        return self._make_geometry(fce.body)

    @property
    def materials(self) -> Iterator[Resource]:
        return map(
            self._make_resource, filter(lambda x: x.name.endswith(".tga"), self.viv.entries)
        )

    @property
    def body_materials(self) -> Iterator[Resource]:
        return filter(lambda x: x.name in self.body_textures, self.materials)

    @property
    def interior_materials(self) -> Iterator[Resource]:
        return filter(lambda x: x.name in self.interior_textures, self.materials)

    @property
    def performance(self) -> dict[str, Any]:
        carp = one(filter(lambda x: x.name == "carp.txt", self.viv.entries))
        parser = CarpData()
        return parser.to_dict(carp.body)

    @property
    def dimensions(self) -> Vector3d:
        fce = one(filter(lambda x: x.name in self.body_geometry, self.viv.entries))
        half_sizes = fce.body.half_sizes
        return Vector3d(x=half_sizes.x * 2, y=half_sizes.y * 2, z=half_sizes.z * 2)

    @property
    def lights(self) -> Iterator[VehicleLight]:
        fce = one(filter(lambda x: x.name in self.body_geometry, self.viv.entries))
        lights = filter(lambda x: x.magic in self.light_types, fce.body.dummies)
        return map(self._make_light, fce.body.light_sources, lights)

    @property
    def engine_audio(self) -> Iterable[EngineAudio]:
        ctb = one(filter(lambda x: x.name == self.ctb, self.viv.entries))
        ltb = one(filter(lambda x: x.name == self.ltb, self.viv.entries))
        bnk = one(filter(lambda x: x.name == self.bnk, self.viv.entries))
        data = BnkData(bnk.body)
        samples = dict(data.sound_streams)
        ctb_engine_sounds = list(self._make_sound_table(EngineAudioType.COAST, ctb))
        ltb_engine_sounds = list(self._make_sound_table(EngineAudioType.LOAD, ltb))

        return self.merge_tables(samples=samples, load=ltb_engine_sounds, coast=ctb_engine_sounds)

    def engine_tables(self, name) -> bytes:
        ctb = one(filter(lambda x: x.name == name, self.viv.entries))
        _ = ctb.body
        return ctb._raw__m_body
