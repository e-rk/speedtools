#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from dataclasses import dataclass
from typing import NamedTuple, Optional, Protocol

from speedtools.parsers import FrdParser, FshParser

CollisionType = FrdParser.ObjectAttribute.CollisionType
ObjectType = FrdParser.ObjectHeader.ObjectType
FshDataType = FshParser.DataType


class Vector3d(NamedTuple):
    x: float
    z: float
    y: float


@dataclass
class Polygon:
    face: tuple[int, ...]
    uv: tuple[tuple[int, int], ...]
    material: str
    backface_culling: bool


class Geometry(Protocol):
    vertices: list[Vector3d]
    polygons: list[Polygon]


class Quaternion(NamedTuple):
    w: float
    x: float
    z: float
    y: float


@dataclass
class Bitmap:
    width: int
    height: int
    rgba: bytes


@dataclass
class Resource:
    name: str
    bitmap: Bitmap
    text: str
    mirrored: bool
    additive: bool


@dataclass
class Animation:
    length: int
    delay: int
    locations: list[Vector3d]
    quaternions: list[Quaternion]


@dataclass
class TrackObject(Geometry):
    location: Optional[Vector3d]
    animation: Optional[Animation]
    vertices: list[Vector3d]
    polygons: list[Polygon]
    collision_type: CollisionType


class CollisionPolygon(NamedTuple):
    face: tuple[int, ...]


@dataclass
class CollisionMesh:
    polygons: list[CollisionPolygon]
    collision_effect: int


@dataclass
class TrackSegment(Geometry):
    vertices: list[Vector3d]
    polygons: list[Polygon]
    collision_meshes: list[CollisionMesh]


@dataclass
class Part(Geometry):
    location: Vector3d
    vertices: list[Vector3d]
    normals: list[Vector3d]
    polygons: list[Polygon]
