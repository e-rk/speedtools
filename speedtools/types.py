#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from math import pi, sqrt
from typing import NamedTuple, Optional, TypeAlias

from speedtools.parsers import FceParser, FrdParser, FshParser

RoadEffect: TypeAlias = FrdParser.DriveablePolygon.RoadEffect
CollisionType: TypeAlias = FrdParser.ObjectAttribute.CollisionType
ObjectType: TypeAlias = FrdParser.ObjectHeader.ObjectType
FshDataType: TypeAlias = FshParser.DataType


class Action(Enum):
    DEFAULT_LOOP = 1
    DESTROY_LOW_SPEED = 2
    DESTROY_HIGH_SPEED = 3


class BlendMode(Enum):
    ALPHA = 1
    ADDITIVE = 2


class ShapeKeyType(Enum):
    DAMAGE = 1


class Edge(Enum):
    FRONT = 0
    LEFT = 1
    BACK = 2
    RIGHT = 3


class VehicleLightType(Enum):
    HEADLIGHT = 1
    TAILLIGHT = 2
    BRAKELIGHT = 3
    REVERSE = 4
    DIRECTIONAL = 5
    SIREN = 6


class Vector3d(NamedTuple):
    x: float
    z: float
    y: float

    @classmethod
    def from_frd_float3(cls, value: FrdParser.Float3) -> Vector3d:
        return Vector3d(x=value.x, y=value.y, z=value.z)

    @classmethod
    def from_frd_int3(cls, value: FrdParser.Int3) -> Vector3d:
        return Vector3d(
            x=value.x / 65536.0,
            y=value.y / 65536.0,
            z=value.z / 65536.0,
        )

    @classmethod
    def from_fce_float3(cls, value: FceParser.Float3) -> Vector3d:
        return Vector3d(x=value.x, y=value.y, z=value.z)

    def horizontal_plane_length(self) -> float:
        return sqrt(self.x**2 + self.z**2)

    def magnitude(self) -> float:
        return sqrt(self.x**2 + self.y**2 + self.z**2)

    def subtract(self, x: Vector3d) -> Vector3d:
        return Vector3d(x=self.x - x.x, y=self.y - x.y, z=self.z - x.z)


class UV(NamedTuple):
    u: float
    v: float


class Quaternion(NamedTuple):
    w: float
    x: float
    z: float
    y: float

    @classmethod
    def from_frd_short4(cls, value: FrdParser.Short4) -> Quaternion:
        return Quaternion(
            x=value.x / 65536.0,
            y=value.y / 65536.0,
            z=value.z / 65536.0,
            w=value.w / 65536.0,
        )


class Color(NamedTuple):
    red: int
    green: int
    blue: int
    alpha: int = 255

    @property
    def rgb(self) -> tuple[int, int, int]:
        return (self.red, self.green, self.blue)

    @property
    def rgb_float(self) -> tuple[float, float, float]:
        return (self.red / 255, self.green / 255, self.blue / 255)

    @property
    def rgba_float(self) -> tuple[float, float, float, float]:
        return (self.red / 255, self.green / 255, self.blue / 255, self.alpha / 255)


class Matrix3x3(NamedTuple):
    x: Vector3d
    z: Vector3d
    y: Vector3d


@dataclass(frozen=True)
class Vertex:
    location: Vector3d
    normal: Vector3d | None = None
    color: Color | None = None


@dataclass(frozen=True)
class BasePolygon:
    face: tuple[int, ...]


@dataclass(frozen=True)
class ShapeKey:
    type: ShapeKeyType
    vertices: Sequence[Vertex]


@dataclass(frozen=True)
class BaseMesh:
    vertices: Sequence[Vertex]
    polygons: Sequence[BasePolygon]

    @property
    def vertex_locations(self) -> Sequence[Vector3d]:
        return [vert.location for vert in self.vertices]

    @property
    def vertex_normals(self) -> Sequence[Vector3d]:
        normals = [vert.normal for vert in self.vertices]
        if None not in normals:
            return normals  # type: ignore[return-value]
        return []

    @property
    def vertex_colors(self) -> Sequence[Color]:
        colors = [vert.color for vert in self.vertices]
        if None not in colors:
            return colors  # type: ignore[return-value]
        return []


@dataclass(frozen=True)
class Polygon(BasePolygon):
    face: tuple[int, ...]
    uv: tuple[UV, ...]
    material: int
    backface_culling: bool
    is_lane: bool = False
    transparent: bool = False
    highly_reflective: bool = False
    non_reflective: bool = False
    animation_ticks: int = 0
    animation_count: int = 0
    billboard: bool = False


@dataclass(frozen=True)
class Animation:
    length: int
    delay: int
    locations: Sequence[Vector3d]
    quaternions: Sequence[Quaternion]


@dataclass(frozen=True)
class AnimationAction:
    action: Action
    animation: Animation


@dataclass(frozen=True)
class DrawableMesh(BaseMesh):
    polygons: Sequence[Polygon]
    shape_keys: Sequence[ShapeKey] = field(default_factory=list)


@dataclass(frozen=True)
class Image:
    data: bytes


@dataclass(frozen=True)
class Bitmap(Image):
    width: int
    height: int


@dataclass(frozen=True)
class SunAttributes:
    angle_theta: float
    angle_rho: float
    radius: float
    rotates: bool
    additive: bool
    in_front: bool


@dataclass(frozen=True)
class Resource:
    name: str
    image: Image
    mirrored: bool = False
    nonmirrored: bool = False
    blend_mode: BlendMode | None = None
    sun_attributes: SunAttributes | None = None


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
    actions: Sequence[AnimationAction] = field(default_factory=tuple)
    transform: Optional[Matrix3x3] = None


@dataclass(frozen=True)
class CollisionPolygon(BasePolygon):
    edges: Sequence[Edge] = field(default_factory=list)
    has_finite_height: bool = False
    has_wall_collision: bool = False


@dataclass(frozen=True)
class CollisionMesh(BaseMesh):
    polygons: Sequence[CollisionPolygon]
    collision_effect: RoadEffect = RoadEffect.not_driveable


@dataclass(frozen=True)
class TrackSegment:
    mesh: DrawableMesh
    collision_meshes: Sequence[CollisionMesh]
    waypoints: Sequence[Vector3d]


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
    color: Color


@dataclass(frozen=True)
class TrackLight(Light):
    blink_interval_ms: int | None
    flare_size: float


@dataclass(frozen=True)
class VehicleLight(Light):
    type: VehicleLightType


@dataclass(frozen=True)
class LightStub:
    location: Vector3d
    glow_id: int


@dataclass(frozen=True)
class DirectionalLight:
    phi: float
    theta: float
    radius: float
    rotates: bool
    in_front: bool
    additive: bool
    resource: Resource

    @property
    def euler_xyz(self) -> Vector3d:
        z = pi / 2 - self.phi
        y = self.theta
        return Vector3d(x=0, y=y, z=z)


@dataclass(frozen=True)
class Camera:
    location: Vector3d
    transform: Matrix3x3


@dataclass(frozen=True)
class Horizon:
    sun_side: Color
    top_side: Color
    opposite_side: Color
