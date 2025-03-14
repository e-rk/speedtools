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

from more_itertools import (
    chunked,
    collapse,
    nth,
    strictly_n,
    transpose,
    unique_everseen,
    unzip,
)

from speedtools.parsers import FrdParser
from speedtools.types import (
    UV,
    Action,
    Animation,
    AnimationAction,
    CollisionMesh,
    CollisionPolygon,
    CollisionType,
    Color,
    DrawableMesh,
    Edge,
    LightStub,
    Matrix3x3,
    ObjectType,
    Polygon,
    Quaternion,
    RoadEffect,
    TrackObject,
    TrackSegment,
    Vector3d,
    Vertex,
)
from speedtools.utils import islicen, remove_unused_vertices

logger = logging.getLogger(__name__)


class FrdData:
    high_poly_chunks = [
        False,  # Low-resolution track geometry
        False,  # Low-resolution misc geometry
        False,  # Medium-resolution track geometry
        False,  # Medium-resolution misc geometry
        True,  # High-resolution track geometry
        True,  # High-resolution misc geometry
        True,  # Road lanes
        True,  # High-resolution misc geometry
        True,  # High-resolution misc geometry
        True,  # High-resolution misc geometry
        True,  # High-resolution misc geometry
    ]
    ROAD_BLOCKS_PER_SEGMENT = 8

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
    def _make_polygon(cls, polygon: FrdParser.Polygon, billboard: bool = False) -> Polygon:
        material = polygon.texture_id
        backface_culling = polygon.backface_culling
        quads_or_triangles = cls._validate_polygon(polygon.face, cls._texture_flags_to_uv(polygon))
        face, uv = unzip(quads_or_triangles)  # pylint: disable=unbalanced-tuple-unpacking
        return Polygon(
            face=tuple(face),
            uv=tuple(uv),
            material=material,
            backface_culling=backface_culling,
            is_lane=polygon.lane,
            non_reflective=True,
            animation_ticks=polygon.animation_ticks,
            animation_count=polygon.texture_count if not polygon.animate_uv else 0,
            billboard=billboard,
        )

    @classmethod
    def _get_object_collision_type(
        cls, segment: Optional[FrdParser.SegmentData], obj: FrdParser.ObjectHeader
    ) -> CollisionType:
        logger.debug(f"Object: {vars(obj)}")
        if (
            obj.type is not ObjectType.normal and obj.type is not ObjectType.billboard
        ) or segment is None:
            return CollisionType.none
        collision_type = CollisionType.none
        with suppress(IndexError):
            object_attribute = segment.object_attributes[obj.attribute_index]
            collision_type = object_attribute.collision_type
        return collision_type

    @classmethod
    def _make_matrix(cls, value: Sequence[float]) -> Matrix3x3:
        val = list(strictly_n(value, 9))
        rows = [Vector3d(x=x, y=y, z=z) for x, y, z in transpose(chunked(val, 3, strict=True))]
        return Matrix3x3(x=rows[0], y=rows[1], z=rows[2])

    @classmethod
    def _make_object(
        cls,
        segment: Optional[FrdParser.SegmentData],
        obj: FrdParser.ObjectHeader,
        extra: FrdParser.ObjectData,
    ) -> TrackObject:
        location = None
        actions = []
        transform = None
        if obj.type in (ObjectType.normal, ObjectType.billboard):
            location = Vector3d(x=obj.location.x, y=obj.location.y, z=obj.location.z)
        if obj.type == ObjectType.special:
            location = Vector3d(x=obj.location.x, y=obj.location.y, z=obj.location.z)
            transform = cls._make_matrix(extra.special.transform)
        elif obj.type == ObjectType.animated:
            locations = [
                Vector3d.from_frd_int3(keyframe.location) for keyframe in extra.animation.keyframes
            ]
            quaternions = [
                Quaternion.from_frd_short4(keyframe.quaternion)
                for keyframe in extra.animation.keyframes
            ]
            animation = Animation(
                length=extra.animation.num_keyframes,
                delay=extra.animation.delay,
                locations=locations,
                quaternions=quaternions,
            )
            actions = [AnimationAction(action=Action.DEFAULT_LOOP, animation=animation)]
        vertex_locations = [Vector3d.from_frd_float3(vertex) for vertex in extra.vertices]
        polygons = [
            cls._make_polygon(polygon=polygon, billboard=obj.type == ObjectType.billboard)
            for polygon in extra.polygons
        ]
        vertex_colors = [
            Color(alpha=shading.alpha, red=shading.red, green=shading.green, blue=shading.blue)
            for shading in extra.vertex_shadings
        ]
        vertices = [
            Vertex(location=loc, color=color)
            for loc, color in zip(vertex_locations, vertex_colors, strict=True)
        ]
        mesh = DrawableMesh(vertices=vertices, polygons=polygons)
        collision_type = cls._get_object_collision_type(segment=segment, obj=obj)
        return TrackObject(
            mesh=mesh,
            collision_type=collision_type,
            location=location,
            actions=actions,
            transform=transform,
        )

    @classmethod
    def _make_collision_polygon(
        cls, segment: FrdParser.SegmentData, polygon: FrdParser.DriveablePolygon
    ) -> CollisionPolygon:
        all_edges = (Edge.FRONT, Edge.LEFT, Edge.BACK, Edge.RIGHT)
        poly_face = segment.chunks[4].polygons[polygon.polygon].face
        face, validated_edges = unzip(  # pylint: disable=unbalanced-tuple-unpacking
            cls._validate_polygon(poly_face, all_edges)
        )
        allowed_edges = list(validated_edges)
        edges: list[Edge] = []
        if polygon.front_edge:
            edges.append(Edge.FRONT)
        if polygon.left_edge:
            edges.append(Edge.LEFT)
        if polygon.back_edge:
            edges.append(Edge.BACK)
        if polygon.right_edge:
            edges.append(Edge.RIGHT)
        edges = list(filter(lambda x: x in allowed_edges, edges))
        return CollisionPolygon(
            face=tuple(face),
            edges=edges,
            has_finite_height=polygon.has_finite_height,
            has_wall_collision=polygon.has_wall_collision,
        )

    @classmethod
    def _make_collision_mesh(
        cls,
        segment: FrdParser.SegmentData,
        road_effect: int,
        driveable_polygons: Iterable[FrdParser.DriveablePolygon],
    ) -> CollisionMesh:
        polygons = [
            cls._make_collision_polygon(segment, polygon) for polygon in driveable_polygons
        ]
        vertex_locations = [Vector3d.from_frd_float3(vertex) for vertex in segment.vertices]
        vertices = [Vertex(location=loc) for loc in vertex_locations]
        mesh = CollisionMesh(
            vertices=vertices, polygons=polygons, collision_effect=RoadEffect(road_effect)
        )
        return remove_unused_vertices(mesh)

    @classmethod
    def _make_collision_meshes(cls, segment: FrdParser.SegmentData) -> Iterator[CollisionMesh]:
        def driveable_polygon_key(driveable_polygon: FrdParser.DriveablePolygon) -> int:
            return int(driveable_polygon.road_effect.value)

        driveable_polygons = sorted(segment.driveable_polygons, key=driveable_polygon_key)
        driveable_mesh_groups = groupby(driveable_polygons, key=driveable_polygon_key)
        meshes = starmap(partial(cls._make_collision_mesh, segment), driveable_mesh_groups)
        return meshes

    @classmethod
    def _make_waypoints(cls, road_block: FrdParser.RoadBlock) -> Vector3d:
        return Vector3d(x=road_block.location.x, y=road_block.location.y, z=road_block.location.z)

    @classmethod
    def _make_track_segment(
        cls,
        header: FrdParser.SegmentHeader,
        segment: FrdParser.SegmentData,
        road_blocks: Iterable[FrdParser.RoadBlock],
    ) -> TrackSegment:
        polygons = chain.from_iterable(chunk.polygons for chunk in cls._high_poly_chunks(segment))
        vertex_locations = [Vector3d.from_frd_float3(vertex) for vertex in segment.vertices]
        track_polygons = [cls._make_polygon(polygon) for polygon in polygons]
        collision_meshes = list(cls._make_collision_meshes(segment))
        vertex_colors = [
            Color(alpha=shading.alpha, red=shading.red, green=shading.green, blue=shading.blue)
            for shading in segment.vertex_shadings
        ]
        vertices = [
            Vertex(location=loc, color=color)
            for loc, color in zip(vertex_locations, vertex_colors, strict=True)
        ]
        mesh = DrawableMesh(vertices=vertices, polygons=track_polygons)
        waypoints = [cls._make_waypoints(block) for block in road_blocks]
        return TrackSegment(
            mesh=mesh,
            collision_meshes=collision_meshes,
            waypoints=waypoints,
        )

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
        return cls._make_objects_from_chunks(segment=segment, chunks=segment.object_chunks)

    @classmethod
    def _make_objects_from_chunks(
        cls, segment: FrdParser.SegmentData | None, chunks: Iterable[FrdParser.ObjectChunk]
    ) -> Iterator[TrackObject]:
        objects = chain.from_iterable(
            zip(obj.objects, obj.object_extras, strict=True) for obj in chunks
        )
        return starmap(partial(cls._make_object, segment), objects)

    @classmethod
    def _make_dummy(cls, dummy: FrdParser.SourceType) -> LightStub:
        location = Vector3d.from_frd_int3(dummy.location)
        identifier = dummy.type & 0x1F
        return LightStub(location=location, glow_id=identifier)

    @property
    def objects(self) -> Iterator[TrackObject]:
        segment_objects = collapse(
            map(self._make_segment_objects, self.frd.segment_data), levels=1
        )
        global_chunks = (global_chunk.chunk for global_chunk in self.frd.global_objects)
        global_objects = self._make_objects_from_chunks(None, global_chunks)
        return chain(segment_objects, global_objects)

    @property
    def track_segments(self) -> Iterator[TrackSegment]:
        road_blocks = starmap(
            lambda i, x: islicen(
                self.frd.road_blocks, i * self.ROAD_BLOCKS_PER_SEGMENT, x.num_road_blocks
            ),
            enumerate(self.frd.segment_headers),
        )
        return map(
            self._make_track_segment, self.frd.segment_headers, self.frd.segment_data, road_blocks
        )

    @property
    def light_dummies(self) -> Iterator[LightStub]:
        lights = chain.from_iterable(segment.light_sources for segment in self.frd.segment_data)
        return map(self._make_dummy, lights)
