#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import NamedTuple, Optional, TypeAlias

from speedtools.parsers import FrdParser, FshParser

RoadEffect: TypeAlias = FrdParser.DriveablePolygon.RoadEffect
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


class Color(NamedTuple):
    alpha: int
    red: int
    green: int
    blue: int

    @property
    def rgb(self) -> tuple[int, int, int]:
        return (self.red, self.green, self.blue)

    @property
    def rgb_float(self) -> tuple[float, float, float]:
        return tuple(map(lambda x: x / 255, self.rgb))  # type: ignore[return-value]


@dataclass(frozen=True)
class BasePolygon:
    face: tuple[int, ...]


@dataclass(frozen=True)
class BaseMesh:
    vertices: Sequence[Vector3d]
    polygons: Sequence[BasePolygon]


@dataclass(frozen=True)
class Polygon(BasePolygon):
    face: tuple[int, ...]
    uv: tuple[UV, ...]
    material: int
    backface_culling: bool


@dataclass(frozen=True)
class Animation:
    length: int
    delay: int
    locations: Sequence[Vector3d]
    quaternions: Sequence[Quaternion]


@dataclass(frozen=True)
class DrawableMesh(BaseMesh):
    polygons: Sequence[Polygon]
    normals: Sequence[Vector3d] = field(default_factory=list)


@dataclass(frozen=True)
class Image:
    data: bytes


@dataclass(frozen=True)
class Bitmap(Image):
    width: int
    height: int


@dataclass(frozen=True)
class Resource:
    name: str
    image: Image
    mirrored: bool = False
    nonmirrored: bool = False
    additive: bool = False


@dataclass(frozen=True)
class ObjectData:
    mesh: DrawableMesh
    location: Optional[Vector3d] = None
    animation: Optional[Animation] = None


@dataclass(frozen=True)
class TrackObject:
    mesh: DrawableMesh
    collision_type: CollisionType
    location: Optional[Vector3d] = None
    animation: Optional[Animation] = None


@dataclass(frozen=True)
class CollisionMesh(BaseMesh):
    collision_effect: RoadEffect


@dataclass(frozen=True)
class TrackSegment:
    mesh: DrawableMesh
    collision_meshes: Sequence[CollisionMesh]


@dataclass(frozen=True)
class Part:
    mesh: DrawableMesh
    name: str
    location: Vector3d


@dataclass(frozen=True)
class LightAttributes:
    identifier: int
    color: Color
    blink_interval_ms: int | None
    flare_size: float


@dataclass(frozen=True)
class Light:
    location: Vector3d
    attributes: LightAttributes


@dataclass(frozen=True)
class LightStub:
    location: Vector3d
    glow_id: int
