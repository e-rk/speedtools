#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Iterator
from itertools import islice

from speedtools.parsers import FceParser, VivParser
from speedtools.types import UV, Image, Part, Polygon, Resource, Vector3d

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)


class VivData(VivParser):
    def _make_polygon(self, polygon: FceParser.Polygon) -> Polygon:
        face = tuple(vertice for vertice in polygon.face)
        uv = tuple(UV(u, 1 - v) for u, v in zip(polygon.u, polygon.v))
        return Polygon(face=face, uv=uv, material=polygon.texture, backface_culling=True)

    @property
    def parts(self) -> Iterator[Part]:
        fce = self.entries[1]
        body = fce.body
        part_vertices_iter = [
            islice(body.vertices, index, index + count)
            for index, count in zip(body.part_vertex_index, body.part_num_vertices)
        ]
        part_normals_iter = [
            islice(body.normals, index, index + count)
            for index, count in zip(body.part_vertex_index, body.part_num_vertices)
        ]
        part_polygons_iter = [
            islice(body.polygons, index, index + count)
            for index, count in zip(body.part_polygon_index, body.part_num_polygons)
        ]
        for part_location, part_vertices, part_normals, part_polygons in zip(
            body.part_locations,
            part_vertices_iter,
            part_normals_iter,
            part_polygons_iter,
            strict=True,
        ):
            location_vect = Vector3d(x=part_location.x, y=part_location.y, z=part_location.z)
            vertices = [Vector3d(x=vert.x, y=vert.y, z=vert.z) for vert in part_vertices]
            normals = [Vector3d(x=normal.x, y=normal.y, z=normal.z) for normal in part_normals]
            polygons = [self._make_polygon(polygon) for polygon in part_polygons]
            yield Part(
                location=location_vect,
                vertices=vertices,
                normals=normals,
                polygons=polygons,
            )

    @property
    def materials(self) -> Iterator[str]:
        for tga in filter(lambda x: x.name.endswith(".tga"), self.entries):
            yield tga.name

    @property
    def materials2(self) -> Iterator[Resource]:
        for tga in filter(lambda x: x.name.endswith("car00.tga"), self.entries):
            image = Image(tga.body)
            yield Resource(name=tga.name, text="", mirrored=False, additive=False, image=image)
