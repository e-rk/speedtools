#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections import namedtuple

from speedtools.parsers import FrdParser
from speedtools.types import Polygon, Quaternion, Vector3d

logger = logging.getLogger(__name__)


class Animation(namedtuple("Animation", ["length", "delay", "positions", "quaternions"])):
    pass


class TrackObject(namedtuple("TrackObject", ["position", "animation", "vertices", "polygons"])):
    pass


class TrackSegment(namedtuple("TrackSegment", ["vertices", "polygons"])):
    pass


class FrdData(FrdParser):
    def _make_polygon(self, polygon):
        material = polygon.texture & 0xFF
        backface_culling = (polygon.hs_texflags & 0x8000) == 0
        material = str(material).zfill(4)
        uvs = []
        face = []
        for vertice, uv in zip(polygon.vertex, self._texture_flags_to_uv(polygon.hs_texflags)):
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
        position = None
        animation = None
        if data.cross_type == 2 or data.cross_type == 4:
            position = Vector3d(x=data.ref.x, y=data.ref.y, z=data.ref.z)
        if data.cross_type == 3:
            positions = [
                Vector3d(x=anim.pt.x / 65536.0, y=anim.pt.y / 65536.0, z=anim.pt.z / 65536.0)
                for anim in extra.anim.anim_data
            ]
            quaternions = [
                Quaternion(x=anim.x, y=anim.y, z=anim.z, w=anim.w) for anim in extra.anim.anim_data
            ]
            animation = Animation(
                length=extra.anim.anim_length,
                delay=extra.anim.anim_delay,
                positions=positions,
                quaternions=quaternions,
            )
        vertices = [Vector3d(x=v.x, y=v.y, z=v.z) for v in extra.vertices]
        polys = [self._make_polygon(polygon) for polygon in extra.polygons.data]
        return TrackObject(
            position=position, animation=animation, vertices=vertices, polygons=polys
        )

    def _texture_flags_to_uv(self, texture_flags):
        uv = [[1, 1], [0, 1], [0, 0], [1, 0]]
        if texture_flags & 32:
            uv[1][1], uv[2][1] = uv[2][1], uv[1][1]
            uv[0][1], uv[3][1] = uv[3][1], uv[0][1]
        if texture_flags & 16:
            uv[0][0], uv[1][0] = uv[1][0], uv[0][0]
            uv[2][0], uv[3][0] = uv[3][0], uv[2][0]
        if texture_flags & 8:
            uv = list(map(lambda x: [1 - x[0], 1 - x[1]], uv))
        if texture_flags & 4:
            uv[0][1] = 1 - uv[0][1]
            uv[1][0] = 1 - uv[1][0]
            uv[2][1] = 1 - uv[2][1]
            uv[3][0] = 1 - uv[3][0]
        return [tuple(item) for item in uv]

    def _high_poly_resources(self, block):
        return [block.polydata[3], block.polydata[4], *block.polydata_obj]

    @property
    def objects(self):
        for block in self.track_block_data:
            for object in block.objs:
                for obj, extra in zip(object.objdata, object.extra):
                    yield self._make_object(obj, extra)
        for object, extra in zip(self.global_objects.objdata, self.global_objects.extra):
            yield self._make_object(object, extra)

    def _make_track_segment(self, vertices, polygons):
        vertices = [Vector3d(x=v.x, y=v.y, z=v.z) for v in vertices]
        polygons = [self._make_polygon(polygon) for polygon in polygons]
        return TrackSegment(vertices=vertices, polygons=polygons)

    @property
    def track_segments(self):
        for block in self.track_block_data:
            for data in self._high_poly_resources(block):
                yield self._make_track_segment(vertices=block.vertices, polygons=data.data)
