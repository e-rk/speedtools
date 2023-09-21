#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from collections.abc import Iterable, Iterator
from enum import Enum
from functools import partial
from itertools import compress, starmap
from pathlib import Path
from typing import NamedTuple

from more_itertools import one

from speedtools.parsers import FceParser, VivParser
from speedtools.types import (
    UV,
    DrawableMesh,
    Image,
    Part,
    Polygon,
    Resource,
    Vector3d,
    Vertex,
)
from speedtools.utils import islicen


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
        ":HLFW": PartAttributes(resolution=Resolution.HIGH, name="front_left_wheel"),
        # High Right Front Wheel
        ":HRFW": PartAttributes(resolution=Resolution.HIGH, name="front_right_wheel"),
        # High Left Middle Wheel
        ":HLMW": PartAttributes(resolution=Resolution.HIGH, name="middle_left_wheel"),
        # High Right Middle Wheel
        ":HRMW": PartAttributes(resolution=Resolution.HIGH, name="middle_right_wheel"),
        # High Left Rear Wheel
        ":HLRW": PartAttributes(resolution=Resolution.HIGH, name="rear_left_wheel"),
        # High Right Rear Wheel
        ":HRRW": PartAttributes(resolution=Resolution.HIGH, name="rear_right_wheel"),
        # Medium Body
        ":MB": PartAttributes(resolution=Resolution.MEDIUM, name="body"),
        # Medium Left Front Wheel
        ":MLFW": PartAttributes(resolution=Resolution.MEDIUM, name="front_left_wheel"),
        # Medium Right Front Wheel
        ":MRFW": PartAttributes(resolution=Resolution.MEDIUM, name="front_right_wheel"),
        # Medium Left Middle Wheel
        ":MLMW": PartAttributes(resolution=Resolution.MEDIUM, name="middle_left_wheel"),
        # Medium Right Middle Wheel
        ":MRMW": PartAttributes(resolution=Resolution.MEDIUM, name="middle_right_wheel"),
        # Medium Left Rear Wheel
        ":MLRW": PartAttributes(resolution=Resolution.MEDIUM, name="rear_left_wheel"),
        # Medium Right Rear Wheel
        ":MRRW": PartAttributes(resolution=Resolution.MEDIUM, name="rear_right_wheel"),
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

    body_geometry = {"car.fce", "hel.fce"}
    body_textures = {"car00.tga", "hel00.tga"}
    interior_geometry = {"dash.fce"}
    interior_textures = {"dash00.tga"}

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
        return Polygon(face=face, uv=uv, material=polygon.texture, backface_culling=True)

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
    def _make_part_mesh(
        cls,
        part_vertices: Iterable[FceParser.Float3],
        part_normals: Iterable[FceParser.Float3],
        part_polygons: Iterable[FceParser.Polygon],
    ) -> DrawableMesh:
        vertex_locations = [Vector3d.from_fce_float3(vert) for vert in part_vertices]
        vertex_normals = [Vector3d.from_fce_float3(normal) for normal in part_normals]
        vertices = [
            Vertex(location=loc, normal=norm)
            for loc, norm in zip(vertex_locations, vertex_normals, strict=True)
        ]
        polygons = [cls._make_polygon(polygon) for polygon in part_polygons]
        return DrawableMesh(vertices=vertices, polygons=polygons)

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
        slice_vert = partial(islicen, fce.vertices)
        part_vertices_iter = map(slice_vert, fce.part_vertex_index, fce.part_num_vertices)
        slice_norm = partial(islicen, fce.normals)
        part_normals_iter = map(slice_norm, fce.part_vertex_index, fce.part_num_vertices)
        slice_norm = partial(islicen, fce.polygons)
        part_polygons_iter = map(slice_norm, fce.part_polygon_index, fce.part_num_polygons)
        meshes = map(
            cls._make_part_mesh,
            part_vertices_iter,
            part_normals_iter,
            part_polygons_iter,
        )
        attributes = list(map(cls._get_part_attributes, fce.part_strings))
        part_data = zip(fce.part_locations, meshes, attributes, strict=True)
        selectors = map(cls._match_attributes, attributes)
        filtered_parts = compress(part_data, selectors)
        return starmap(cls._make_part, filtered_parts)

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
