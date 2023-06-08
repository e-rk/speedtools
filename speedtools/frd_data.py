#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator, Sequence
from contextlib import suppress
from functools import partial
from itertools import chain, compress, groupby, starmap
from pathlib import Path
from typing import Any, Optional

from more_itertools import collapse, nth, unique_everseen, unzip

from speedtools.parsers import FrdParser
from speedtools.types import (
    UV,
    Animation,
    BasePolygon,
    CollisionMesh,
    CollisionType,
    DrawableMesh,
    LightStub,
    ObjectType,
    Polygon,
    Quaternion,
    RoadEffect,
    TrackObject,
    TrackSegment,
    Vector3d,
)

logger = logging.getLogger(__name__)


class FrdData:
    high_poly_chunks = [
        False,  # Low-resolution track geometry
        False,  # Low-resolution misc geometry
        False,  # Medium-resolution track geometry
        False,  # Medium-resolution misc geometry
        True,  # High-resolution track geometry
        True,  # High-resolution misc geometry
        False,  # Road lanes
        True,  # High-resolution misc geometry
        True,  # High-resolution misc geometry
        True,  # High-resolution misc geometry
        True,  # High-resolution misc geometry
    ]

    def __init__(self, parser: FrdParser) -> None:
        self.frd = parser

    @classmethod
    def from_file(cls, path: Path) -> FrdData:
        parser = FrdParser.from_file(path)
        return cls(parser)

    @classmethod
    def _validate_polygon(
        cls, face: Sequence[int], *iterables: Iterable[Any]
    ) -> Iterator[tuple[Any, ...]]:
        polygon_data_zipped = zip(face, *iterables)
        return unique_everseen(polygon_data_zipped, key=lambda x: nth(x, 0))

    @classmethod
    def _make_polygon(cls, polygon: FrdParser.Polygon) -> Polygon:
        material = polygon.texture & 0x7FF
        backface_culling = polygon.backface_culling
        quads_or_triangles = cls._validate_polygon(polygon.face, cls._texture_flags_to_uv(polygon))
        face, uv = unzip(quads_or_triangles)  # pylint: disable=unbalanced-tuple-unpacking
        return Polygon(
            face=tuple(face),
            uv=tuple(uv),
            material=material,
            backface_culling=backface_culling,
        )

    @classmethod
    def _get_object_collision_type(
        cls, segment: Optional[FrdParser.SegmentData], obj: FrdParser.ObjectHeader
    ) -> CollisionType:
        logger.info(f"Object: {vars(obj)}")
        if (
            obj.type is not ObjectType.normal1 and obj.type is not ObjectType.normal2
        ) or segment is None:
            return CollisionType.none
        collision_type = CollisionType.none
        with suppress(IndexError):
            object_attribute = segment.object_attributes[obj.attribute_index]
            collision_type = object_attribute.collision_type
        return collision_type

    @classmethod
    def _int3_to_vector3d(cls, location: FrdParser.Int3) -> Vector3d:
        return Vector3d(x=location.x / 65536.0, y=location.y / 65536.0, z=location.z / 65536.0)

    @classmethod
    def _make_object(
        cls,
        segment: Optional[FrdParser.SegmentData],
        obj: FrdParser.ObjectHeader,
        extra: FrdParser.ObjectData,
    ) -> TrackObject:
        location = None
        animation = None
        if obj.type in (ObjectType.normal1, ObjectType.normal2):
            location = Vector3d(x=obj.location.x, y=obj.location.y, z=obj.location.z)
        if obj.type == ObjectType.animated:
            locations = [
                Vector3d(
                    x=keyframe.location.x / 65536.0,
                    y=keyframe.location.y / 65536.0,
                    z=keyframe.location.z / 65536.0,
                )
                for keyframe in extra.animation.keyframes
            ]
            quaternions = [
                Quaternion(
                    x=keyframe.quaternion.x,
                    y=keyframe.quaternion.y,
                    z=keyframe.quaternion.z,
                    w=keyframe.quaternion.w,
                )
                for keyframe in extra.animation.keyframes
            ]
            animation = Animation(
                length=extra.animation.num_keyframes,
                delay=extra.animation.delay,
                locations=locations,
                quaternions=quaternions,
            )
        vertices = [Vector3d(x=vertice.x, y=vertice.y, z=vertice.z) for vertice in extra.vertices]
        polygons = [cls._make_polygon(polygon) for polygon in extra.polygons]
        mesh = DrawableMesh(vertices=vertices, polygons=polygons)
        collision_type = cls._get_object_collision_type(segment=segment, obj=obj)
        return TrackObject(
            mesh=mesh, collision_type=collision_type, location=location, animation=animation
        )

    @classmethod
    def _make_collision_mesh(
        cls,
        segment: FrdParser.SegmentData,
        road_effect: int,
        driveable_polygons: FrdParser.DriveablePolygon,
    ) -> CollisionMesh:
        polygons = [
            BasePolygon(face=segment.chunks[4].polygons[polygon.polygon].face)
            for polygon in driveable_polygons
        ]
        vertices = [
            Vector3d(x=vertice.x, y=vertice.y, z=vertice.z) for vertice in segment.vertices
        ]
        return CollisionMesh(
            vertices=vertices, polygons=polygons, collision_effect=RoadEffect(road_effect)
        )

    @classmethod
    def _make_collision_meshes(cls, segment: FrdParser.SegmentData) -> Iterator[CollisionMesh]:
        def driveable_polygon_key(driveable_polygon: FrdParser.DriveablePolygon) -> int:
            return int(driveable_polygon.road_effect.value)

        driveable_polygons = sorted(segment.driveable_polygons, key=driveable_polygon_key)
        driveable_mesh_groups = groupby(driveable_polygons, key=driveable_polygon_key)
        meshes = starmap(partial(cls._make_collision_mesh, segment), driveable_mesh_groups)
        return filter(lambda x: x.collision_effect is not RoadEffect.not_driveable, meshes)

    @classmethod
    def _make_track_segment(cls, segment: FrdParser.SegmentData) -> TrackSegment:
        polygons = chain.from_iterable(chunk.polygons for chunk in cls._high_poly_chunks(segment))
        vertices = [
            Vector3d(x=vertice.x, y=vertice.y, z=vertice.z) for vertice in segment.vertices
        ]
        track_polygons = [cls._make_polygon(polygon) for polygon in polygons]
        collision_meshes = list(cls._make_collision_meshes(segment))
        mesh = DrawableMesh(vertices=vertices, polygons=track_polygons)
        return TrackSegment(mesh=mesh, collision_meshes=collision_meshes)

    @classmethod
    def _texture_flags_to_uv(cls, polygon: FrdParser.Polygon) -> list[UV]:
        uv = [[1, 1], [0, 1], [0, 0], [1, 0]]
        if polygon.mirror_y:
            uv[1][1], uv[2][1] = uv[2][1], uv[1][1]
            uv[0][1], uv[3][1] = uv[3][1], uv[0][1]
        if polygon.mirror_x:
            uv[0][0], uv[1][0] = uv[1][0], uv[0][0]
            uv[2][0], uv[3][0] = uv[3][0], uv[2][0]
        if polygon.invert:
            uv = list(map(lambda x: [1 - x[0], 1 - x[1]], uv))
        if polygon.rotate:
            uv[0][1] = 1 - uv[0][1]
            uv[1][0] = 1 - uv[1][0]
            uv[2][1] = 1 - uv[2][1]
            uv[3][0] = 1 - uv[3][0]
        return [UV(u=item[0], v=item[1]) for item in uv]

    @classmethod
    def _high_poly_chunks(cls, block: FrdParser.SegmentData) -> Iterable[FrdParser.SegmentData]:
        return compress(block.chunks, cls.high_poly_chunks)

    @classmethod
    def _make_segment_objects(cls, segment: FrdParser.SegmentData) -> Iterator[TrackObject]:
        objects = chain.from_iterable(
            zip(obj.objects, obj.object_extras, strict=True) for obj in segment.object_chunks
        )
        return starmap(partial(cls._make_object, segment), objects)

    @classmethod
    def _make_dummy(cls, dummy: FrdParser.SourceType) -> LightStub:
        location = cls._int3_to_vector3d(dummy.location)
        identifier = dummy.type & 0x1F
        return LightStub(location=location, glow_id=identifier)

    @property
    def objects(self) -> Iterator[TrackObject]:
        segment_objects = collapse(
            map(self._make_segment_objects, self.frd.segment_data), levels=1
        )
        global_objects = map(
            partial(self._make_object, None),
            self.frd.global_objects.objects,
            self.frd.global_objects.object_extras,
        )
        return chain(segment_objects, global_objects)

    @property
    def track_segments(self) -> Iterator[TrackSegment]:
        return map(self._make_track_segment, self.frd.segment_data)

    @property
    def light_dummies(self) -> Iterator[LightStub]:
        lights = chain.from_iterable(segment.light_sources for segment in self.frd.segment_data)
        return map(self._make_dummy, lights)
