#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import NamedTuple, Optional, Protocol, TypeAlias

from speedtools.parsers import FrdParser, FshParser

CollisionType: TypeAlias = FrdParser.ObjectAttribute.CollisionType
ObjectType: TypeAlias = FrdParser.ObjectHeader.ObjectType
FshDataType: TypeAlias = FshParser.DataType


class Vector3d(NamedTuple):
    x: float
    z: float
    y: float


class UV(NamedTuple):
    u: float
    v: float


class Quaternion(NamedTuple):
    w: float
    x: float
    z: float
    y: float


class BasePolygon(Protocol):
    face: tuple[int, ...]


class BaseMesh(Protocol):
    vertices: Sequence[Vector3d]
    polygons: Sequence[BasePolygon]
    normals: Sequence[Vector3d]


@dataclass(frozen=True)
class Polygon(BasePolygon):
    face: tuple[int, ...]
    uv: tuple[UV, ...]
    material: int
    backface_culling: bool


@dataclass
class Animation:
    length: int
    delay: int
    locations: Sequence[Vector3d]
    quaternions: Sequence[Quaternion]


class DrawableMesh(BaseMesh, Protocol):
    polygons: Sequence[Polygon]
    location: Optional[Vector3d]
    animation: Optional[Animation]


@dataclass(frozen=True)
class Bitmap:
    width: int
    height: int
    rgba: bytes


@dataclass(frozen=True)
class Resource:
    name: str
    bitmap: Bitmap
    text: str
    mirrored: bool
    additive: bool


@dataclass
class TrackObject(DrawableMesh):
    collision_type: CollisionType
    vertices: Sequence[Vector3d]
    polygons: Sequence[Polygon]
    location: Optional[Vector3d] = None
    animation: Optional[Animation] = None
    normals: Sequence[Vector3d] = field(default_factory=list)


@dataclass(frozen=True)
class CollisionPolygon(BasePolygon):
    face: tuple[int, ...]


@dataclass
class CollisionMesh(BaseMesh):
    collision_effect: int
    vertices: Sequence[Vector3d]
    polygons: Sequence[BasePolygon]
    normals: Sequence[Vector3d] = field(default_factory=list)


@dataclass
class TrackSegment(DrawableMesh):
    collision_meshes: Sequence[CollisionMesh]
    vertices: Sequence[Vector3d]
    polygons: Sequence[Polygon]
    location: Optional[Vector3d] = None
    animation: Optional[Animation] = None
    normals: Sequence[Vector3d] = field(default_factory=list)


@dataclass
class Part(DrawableMesh):
    vertices: Sequence[Vector3d]
    polygons: Sequence[Polygon]
    location: Optional[Vector3d] = None
    animation: Optional[Animation] = None
    normals: Sequence[Vector3d] = field(default_factory=list)
