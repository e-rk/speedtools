#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections import namedtuple
from itertools import chain, compress

from speedtools.parsers import FrdParser
from speedtools.types import Polygon, Quaternion, Vector3d

logger = logging.getLogger(__name__)


class Animation(namedtuple("Animation", ["length", "delay", "locations", "quaternions"])):
    pass


class TrackObject(namedtuple("TrackObject", ["location", "animation", "vertices", "polygons"])):
    pass


class TrackSegment(namedtuple("TrackSegment", ["vertices", "polygons"])):
    pass


class FrdData(FrdParser):
    def _make_polygon(self, polygon):
        material = polygon.texture & 0xFF
        backface_culling = polygon.backface_culling
        material = str(material).zfill(4)
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

    def _make_object(self, data, extra):
        location = None
        animation = None
        if data.type == data.ObjectType.normal1 or data.type == data.ObjectType.normal2:
            location = Vector3d(x=data.location.x, y=data.location.y, z=data.location.z)
        if data.type == data.ObjectType.animated:
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
        return TrackObject(
            location=location, animation=animation, vertices=vertices, polygons=polys
        )

    def _make_track_segment(self, segment, polygons):
        vertices = [
            Vector3d(x=vertice.x, y=vertice.y, z=vertice.z) for vertice in segment.vertices
        ]
        polygons = [self._make_polygon(polygon) for polygon in polygons]
        return TrackSegment(vertices=vertices, polygons=polygons)

    def _texture_flags_to_uv(self, polygon):
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
        return [tuple(item) for item in uv]

    def _high_poly_chunks(self, block):
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
    def objects(self):
        object_chunks = chain.from_iterable(block.object_chunks for block in self.segment_data)
        objects = chain.from_iterable(
            zip(object.objects, object.object_extras, strict=True) for object in object_chunks
        )
        for object, extra in chain(
            objects,
            zip(self.global_objects.objects, self.global_objects.object_extras, strict=True),
        ):
            yield self._make_object(object, extra)

    @property
    def track_segments(self):
        for segment in self.segment_data:
            polygons = chain.from_iterable(
                chunk.polygons for chunk in self._high_poly_chunks(segment)
            )
            yield self._make_track_segment(segment=segment, polygons=polygons)
