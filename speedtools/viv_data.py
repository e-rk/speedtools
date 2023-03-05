#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections import namedtuple

from speedtools.parser.viv import Viv
from speedtools.types import Polygon, Vector3d

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)


class Part(namedtuple("Part", ["position", "vertices", "normals", "polygons"])):
    pass


class VivData(Viv):
    def _make_polygon(self, polygon):
        face = tuple(vertice for vertice in polygon.vertices)
        uv = tuple((u, 1 - v) for u, v in zip(polygon.u, polygon.v))
        return Polygon(face=face, uv=uv, material=polygon.texture, backface_culling=True)

    @property
    def parts(self):
        fce = self.entries[1]
        body = fce.body
        for position, vertex_index, vertex_num, polygon_index, polygon_num in zip(
            body.parts,
            body.part_vertex_index,
            body.part_num_vertices,
            body.part_triangle_index,
            body.part_num_triangles,
            strict=True,
        ):
            position_vect = Vector3d(x=position.x, y=position.y, z=position.z)
            vertices = [
                Vector3d(x=vert.x, y=vert.y, z=vert.z)
                for vert in body.vertices[vertex_index: vertex_index + vertex_num]
            ]
            normals = [
                Vector3d(x=normal.x, y=normal.y, z=normal.z)
                for normal in body.normals[vertex_index: vertex_index + vertex_num]
            ]
            polygons = [
                self._make_polygon(polygon)
                for polygon in body.polygons[polygon_index: polygon_index + polygon_num]
            ]
            yield Part(
                position=position_vect,
                vertices=vertices,
                normals=normals,
                polygons=polygons,
            )

    @property
    def materials(self):
        for tga in filter(lambda x: x.name.endswith(".tga"), self.entries):
            yield tga.name
