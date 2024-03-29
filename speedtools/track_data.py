#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import suppress
from functools import lru_cache, partial, partialmethod, reduce
from itertools import accumulate, chain, cycle, repeat, starmap
from math import atan2, cos, tau
from operator import add
from pathlib import Path
from typing import Tuple, TypeVar

from speedtools.cam_data import CamData
from speedtools.can_data import CanData
from more_itertools import collapse, map_except, take, triplewise
from speedtools.frd_data import FrdData
from speedtools.fsh_data import FshData
from speedtools.parsers import HeightsParser
from speedtools.tr_ini import TrackIni
from speedtools.types import (
    Action,
    AnimationAction,
    Camera,
    CollisionType,
    CollisionPolygon,
    Color,
    BaseMesh,
    CollisionMesh,
    DirectionalLight,
    Edge,
    Horizon,
    Light,
    LightAttributes,
    LightStub,
    Polygon,
    Resource,
    RoadEffect,
    TrackObject,
    TrackSegment,
    Vector3d,
    Vertex,
)
from speedtools.utils import (
    islicen,
    make_subset_mesh,
    merge_mesh,
    slicen,
    unique_named_resources,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")


class TrackData:
    ANIMATION_ACTIONS = (
        (Action.DESTROY_LOW_SPEED, "TR02.CAN"),
        (Action.DESTROY_HIGH_SPEED, "TR03.CAN"),
    )
    SUN_DISTANCE = 3000
    ANIMATION_FPS = 64
    SFX_RESOURCE_FILE = Path("Data", "GAMEART", "SFX.FSH")

    def __init__(
        self,
        directory: Path,
        game_root: Path,
        mirrored: bool = False,
        night: bool = False,
        weather: bool = False,
    ) -> None:
        logger.debug(f"Opening directory {directory}")
        self.frd: FrdData = self.tr_open(
            constructor=FrdData.from_file,
            directory=directory,
            prefix="TR",
            postfix=".FRD",
            mirrored=mirrored,
            night=night,
            weather=weather,
        )
        self.qfs: FshData = self.tr_open(
            constructor=FshData.from_file,
            directory=directory,
            prefix="TR",
            postfix="0.QFS",
            mirrored=mirrored,
            night=night,
            weather=weather,
        )
        self.sky: FshData = self.tr_open(
            constructor=FshData.from_file,
            directory=directory,
            prefix="SKY",
            postfix=".QFS",
            mirrored=mirrored,
            night=night,
            weather=weather,
        )
        self.ini: TrackIni = self.tr_open(
            constructor=TrackIni.from_file,
            directory=directory,
            prefix="TR",
            postfix=".INI",
            mirrored=mirrored,
            night=night,
            weather=weather,
        )
        self.cam: CamData = self.tr_open(
            constructor=CamData.from_file,
            directory=directory,
            prefix="TR",
            postfix=".CAM",
            mirrored=mirrored,
            night=night,
            weather=weather,
        )
        self.sfx: FshData = FshData.from_file(Path(game_root, self.SFX_RESOURCE_FILE))
        self.can: Sequence[tuple[Action, CanData]] = self.tr_can_open(directory=directory)
        self.heights: HeightsParser = HeightsParser.from_file(Path(directory, "HEIGHTS.SIM"))
        self.resources: dict[int, Resource] = {}
        self.sfx_resources: dict[str, Resource] = {}
        self.light_glows: dict[int, LightAttributes] = {}
        self.mirrored: bool = mirrored
        self.night: bool = night
        self.weather: bool = weather

    @classmethod
    def tr_open(
        cls,
        constructor: Callable[[Path], T],
        directory: Path,
        prefix: str,
        postfix: str,
        mirrored: bool = False,
        night: bool = False,
        weather: bool = False,
    ) -> T:
        if weather and night:
            try_options = ["NW", "N", ""]
        elif night:
            try_options = ["N", ""]
        elif weather:
            try_options = ["W", ""]
        else:
            try_options = [""]
        for variant in try_options:
            with suppress(FileNotFoundError):
                return constructor(Path(directory, f"{prefix}{variant}{postfix}"))
        raise FileNotFoundError(f"File {prefix}{postfix} or its variants not found")

    @classmethod
    def tr_can_open(cls, directory: Path) -> Sequence[tuple[Action, CanData]]:
        data = [
            (action, CanData.from_file(Path(directory, filename)))
            for action, filename in cls.ANIMATION_ACTIONS
        ]
        return data

    @classmethod
    def _finalize_object(cls, actions: Iterable[AnimationAction], obj: TrackObject) -> TrackObject:
        object_actions = list(obj.actions)
        if obj.collision_type is CollisionType.destructible:
            filtered_actions = filter(
                lambda x: x.action in (Action.DESTROY_LOW_SPEED, Action.DESTROY_HIGH_SPEED),
                actions,
            )
            for action in filtered_actions:
                object_actions.append(action)
        return TrackObject(
            mesh=obj.mesh,
            collision_type=obj.collision_type,
            location=obj.location,
            actions=object_actions,
            transform=obj.transform,
        )

    def _raise_vertices(cls, height: float, vertice: Vector3d) -> Vector3d:
        y = vertice.y + height
        return Vector3d(x=vertice.x, y=y, z=vertice.z)

    @classmethod
    def _raise_vertex(cls, height: Tuple[Vector3d, float], vertice: Vertex) -> Vertex:
        _, h = height
        y = vertice.location.y + h
        location = Vector3d(x=vertice.location.x, y=y, z=vertice.location.z)
        return Vertex(location=location)

    @classmethod
    def _make_wall_polygon(cls, offset: int, f: tuple[int, ...], edge: Edge) -> CollisionPolygon:
        face = None
        if edge is Edge.FRONT:
            face = (f[1], f[0], offset + f[0], offset + f[1])
        if edge is Edge.LEFT:
            face = (f[2], f[1], offset + f[1], offset + f[2])
        if edge is Edge.BACK:
            face = (f[3], f[2], offset + f[2], offset + f[3])
        if edge is Edge.RIGHT:
            face = (f[0], f[3], offset + f[3], offset + f[0])
        if not face:
            raise RuntimeError("Error during wall creation")
        return CollisionPolygon(face=face)

    @classmethod
    def _make_wall_from_polygon(
        cls, offset: int, polygon: CollisionPolygon
    ) -> Iterable[CollisionPolygon]:
        return map_except(
            partial(cls._make_wall_polygon, offset, polygon.face),
            polygon.edges,
            RuntimeError,
            IndexError,
        )

    @classmethod
    def _make_wall_mesh(cls, floor: CollisionMesh, ceiling: CollisionMesh) -> CollisionMesh:
        merged = merge_mesh(floor, ceiling)
        polys_with_walls = filter(lambda x: x.has_wall_collision, floor.polygons)
        polygons = collapse(
            map(
                lambda x: cls._make_wall_from_polygon(len(floor.vertices), x),
                polys_with_walls,
            )
        )
        walls = BaseMesh(vertices=merged.vertices, polygons=list(polygons))
        mesh_constructor = partial(CollisionMesh)
        return make_subset_mesh(
            mesh=walls,
            mesh_constructor=mesh_constructor,
            polygon_constructors=repeat(CollisionPolygon),
            selectors=repeat(True),
        )

    @classmethod
    def _make_ceiling(
        cls, heights: Sequence[Tuple[Vector3d, float]], mesh: CollisionMesh
    ) -> CollisionMesh:
        @lru_cache
        def sort_key(vertex: Vertex, x: Tuple[Vector3d, float]) -> float:
            location, _ = x
            diff = vertex.location.subtract(location)
            return diff.magnitude()

        def get_height(x: Tuple[Vector3d, float]) -> float:
            _, height = x
            return height

        k = map(lambda x: partial(sort_key, x), mesh.vertices)
        f = partial(sorted, heights)
        closest = map(lambda x: f(key=x), k)
        target_heights = map(partial(take, 3), closest)
        target_heights = map(partial(min, key=get_height), target_heights)
        vertices = [
            cls._raise_vertex(height, vertice)
            for height, vertice in zip(target_heights, mesh.vertices, strict=True)
        ]
        return CollisionMesh(
            vertices=vertices, polygons=mesh.polygons, collision_effect=RoadEffect.not_driveable
        )

    @classmethod
    def _finalize_segment(
        cls, heights: Iterable[Tuple[Vector3d, float]], segment: TrackSegment
    ) -> TrackSegment:
        heights = list(heights)
        floor = segment.collision_meshes
        ceiling = [cls._make_ceiling(heights, mesh) for mesh in segment.collision_meshes]
        walls = [
            cls._make_wall_mesh(floor, ceiling)
            for floor, ceiling in zip(floor, ceiling, strict=True)
        ]
        collision_meshes = chain(floor, walls)
        return TrackSegment(
            mesh=segment.mesh, collision_meshes=list(collision_meshes), waypoints=segment.waypoints
        )

    @classmethod
    def _make_waypoint_height_pair(
        cls,
        first: Tuple[Iterable[Vector3d], Iterable[float]],
        middle: Tuple[Iterable[Vector3d], Iterable[float]],
        last: Tuple[Iterable[Vector3d], Iterable[float]],
    ) -> Iterable[Tuple[Vector3d, float]]:
        fw, fh = first
        mw, mh = middle
        lw, lh = last
        waypoints = chain(fw, mw, lw)
        heights = chain(fh, mh, lh)
        return zip(waypoints, heights, strict=True)

    @property
    def objects(self) -> Iterator[TrackObject]:
        actions = [AnimationAction(action, can.animation) for action, can in self.can]
        return map(partial(self._finalize_object, actions), self.frd.objects)

    @property
    def track_segments(self) -> Iterator[TrackSegment]:
        segments = list(self.frd.track_segments)
        height_num = map(lambda x: len(x.waypoints), segments)
        height_idx = accumulate(segments, func=lambda x, y: x + len(y.waypoints), initial=0)
        heights = map(lambda i, n: slicen(self.heights.heights, i, n), height_idx, height_num)
        waypoints = map(lambda x: x.waypoints, segments)
        waypoints_and_heights = list(zip(waypoints, heights))
        waypoints_and_heights = [
            waypoints_and_heights[-1],
            *waypoints_and_heights,
            waypoints_and_heights[0],
        ]
        triples = triplewise(waypoints_and_heights)
        chained = starmap(self._make_waypoint_height_pair, triples)
        return map(self._finalize_segment, chained, segments)

    @property
    def track_resources(self) -> Iterator[Resource]:
        return self.qfs.resources

    def _init_resources(self) -> None:
        if self.mirrored:
            resources = filter(lambda resource: not resource.nonmirrored, self.qfs.resources)
        else:
            resources = filter(lambda resource: not resource.mirrored, self.qfs.resources)
        unique_named = unique_named_resources(iterable=resources)
        self.resources = dict(enumerate(unique_named))
        self.sfx_resources = {res.name: res for res in self.sfx.resources}

    def get_polygon_material(self, polygon: Polygon) -> Resource:
        mat = polygon.material
        if not self.resources:
            self._init_resources()
        if polygon.is_lane:
            return self.sfx_resources[f"lin{mat}"]
        return self.resources[mat]

    def _make_light(self, stub: LightStub) -> Light:
        attributes = self.light_glows[stub.glow_id]
        return Light(location=stub.location, attributes=attributes)

    @property
    def lights(self) -> Iterator[Light]:
        if not self.light_glows:
            for attribute in self.ini.glows:
                self.light_glows[attribute.identifier] = attribute
        return map(self._make_light, self.frd.light_dummies)

    @property
    def directional_light(self) -> DirectionalLight | None:
        sun = self.ini.sun
        if sun is None:
            return None
        # Angles in INI are in turns. Turns are converted to radians here.
        # The INI angleRho value is not really a spherical coordinate.
        # Some approximations are done here to convert to spherical coordinates.
        rho = sun.angle_rho * tau
        z = self.SUN_DISTANCE * cos(rho)
        phi = atan2(z, self.SUN_DISTANCE)
        theta = sun.angle_theta * tau
        return DirectionalLight(rho=phi, theta=theta, radius=sun.radius)

    @property
    def cameras(self) -> Iterable[Camera]:
        return self.cam.cameras

    @property
    def ambient_color(self) -> Color:
        return self.ini.ambient_color

    @property
    def horizon(self) -> Horizon:
        return self.ini.horizon
