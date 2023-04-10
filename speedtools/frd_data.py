#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Iterable, Iterator
from contextlib import suppress
from itertools import chain, compress, groupby
from typing import Optional

from speedtools.parsers import FrdParser
from speedtools.types import (
    UV,
    Animation,
    CollisionMesh,
    CollisionPolygon,
    CollisionType,
    ObjectType,
    Polygon,
    Quaternion,
    TrackObject,
    TrackSegment,
    Vector3d,
)

logger = logging.getLogger(__name__)


class FrdData(FrdParser):
    def _make_polygon(self, polygon: FrdParser.Polygon) -> Polygon:
        material = polygon.texture & 0x7FF
        backface_culling = polygon.backface_culling
        uvs = []
        face = []
        for vertice, uv in zip(polygon.face, self._texture_flags_to_uv(polygon), strict=True):
            if vertice in face:
                logger.debug("Polygon is not a quad. Converting into triangle.")
                continue
            uvs.append(uv)
            face.append(vertice)
        return Polygon(
            face=tuple(face),
            uv=tuple(uvs),
            material=material,
            backface_culling=backface_culling,
        )

    def _get_object_collision_type(
        self, segment: Optional[FrdParser.SegmentData], object: FrdParser.ObjectHeader
    ) -> CollisionType:
        logger.info(f"Object: {vars(object)}")
        if (
            object.type is not ObjectType.normal1 and object.type is not ObjectType.normal2
        ) or segment is None:
            return CollisionType.none
        collision_type = CollisionType.none
        with suppress(IndexError):
            object_attribute = segment.object_attributes[object.attribute_index]
            collision_type = object_attribute.collision_type
        return collision_type

    def _make_object(
        self,
        segment: Optional[FrdParser.SegmentData],
        object: FrdParser.ObjectHeader,
        extra: FrdParser.ObjectData,
    ) -> TrackObject:
        location = None
        animation = None
        if object.type == ObjectType.normal1 or object.type == ObjectType.normal2:
            location = Vector3d(x=object.location.x, y=object.location.y, z=object.location.z)
        if object.type == ObjectType.animated:
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
        polys = [self._make_polygon(polygon) for polygon in extra.polygons]
        collision_type = self._get_object_collision_type(segment=segment, object=object)
        return TrackObject(
            location=location,
            animation=animation,
            vertices=vertices,
            polygons=polys,
            collision_type=collision_type,
        )

    def _make_collision_mesh(self, segment: FrdParser.SegmentData) -> Iterator[CollisionMesh]:
        driveable_polygons = sorted(
            segment.driveable_polygons, key=lambda x: int(x.collision_flags) & 0x0F
        )
        driveable_mesh_groups = groupby(
            driveable_polygons, key=lambda x: int(x.collision_flags) & 0x0F
        )
        for key, group in driveable_mesh_groups:
            if key == 0:
                continue
            polygons = [
                CollisionPolygon(face=segment.chunks[4].polygons[polygon.polygon].face)
                for polygon in group
            ]
            yield CollisionMesh(
                vertices=[
                    Vector3d(x=vertice.x, y=vertice.y, z=vertice.z) for vertice in segment.vertices
                ],
                polygons=polygons,
                collision_effect=key,
            )

    def _make_track_segment(
        self, segment: FrdParser.SegmentData, polygons: Iterable[FrdParser.Polygon]
    ) -> TrackSegment:
        vertices = [
            Vector3d(x=vertice.x, y=vertice.y, z=vertice.z) for vertice in segment.vertices
        ]
        track_polygons = [self._make_polygon(polygon) for polygon in polygons]
        collision_meshes = list(self._make_collision_mesh(segment))
        return TrackSegment(
            vertices=vertices, polygons=track_polygons, collision_meshes=collision_meshes
        )

    def _texture_flags_to_uv(self, polygon: FrdParser.Polygon) -> list[UV]:
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

    def _high_poly_chunks(self, block: FrdParser.SegmentData) -> Iterable[FrdParser.SegmentData]:
        return compress(
            block.chunks,
            [
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
            ],
        )

    @property
    def objects(self) -> Iterator[TrackObject]:
        for segment in self.segment_data:
            objects = chain.from_iterable(
                zip(object.objects, object.object_extras, strict=True)
                for object in segment.object_chunks
            )
            for object, extra in objects:
                yield self._make_object(
                    segment=segment,
                    object=object,
                    extra=extra,
                )
        for object, extra in zip(
            self.global_objects.objects, self.global_objects.object_extras, strict=True
        ):
            yield self._make_object(segment=None, object=object, extra=extra)

    @property
    def track_segments(self) -> Iterator[TrackSegment]:
        for segment in self.segment_data:
            polygons = chain.from_iterable(
                chunk.polygons for chunk in self._high_poly_chunks(segment)
            )
            yield self._make_track_segment(segment=segment, polygons=polygons)
