#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import suppress
from dataclasses import replace
from fnmatch import fnmatch
from functools import partial, reduce
from itertools import accumulate, chain, starmap
from math import atan2, cos, tau
from pathlib import Path
from typing import TypeVar

from more_itertools import collapse, filter_map, one, take, triplewise

from speedtools.bnk_data import BnkData
from speedtools.cam_data import CamData
from speedtools.can_data import CanData
from speedtools.frd_data import FrdData
from speedtools.fsh_data import FshData
from speedtools.parsers import HeightsParser
from speedtools.tr_ini import TrackIni
from speedtools.types import (
    Action,
    AnimationAction,
    AudioSource,
    Camera,
    CollisionMesh,
    CollisionPolygon,
    CollisionType,
    Color,
    DirectionalLight,
    Edge,
    Horizon,
    LightAttributes,
    LightStub,
    Polygon,
    Resource,
    SoundStub,
    TrackLight,
    TrackObject,
    TrackSegment,
    Vector3d,
    Vertex,
)
from speedtools.utils import (
    get_path_case_insensitive,
    merge_mesh,
    remove_unused_vertices,
    slicen,
    unique_named_resources,
    validate_face,
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
    AUDIO_DATA_PATH = Path("Data", "AUDIO", "SFX")
    AUDIO_MAPPING = {
        "HILLS": 12,
        "GERMANY": 15,
        "COASTAL": 10,
        "PARK": 13,
        "FRANCE": 16,
        "UK": 14,
        "SNOWY": 11,
        "GT1": 17,
        "GT2": 17,
        "GT3": 17,
        "HOMETOWN": 0,
        "REDROCK": 1,
        "ATLANTIC": 2,
        "ROCKYPAS": 3,
        "COUNTRY": 4,
        "LOSTCANY": 5,
        "AQUATICA": 6,
        "SUMMIT": 7,
        "EMPIRE": 8,
    }

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
        self.sfx: FshData = FshData.from_file(
            get_path_case_insensitive(game_root, Path(game_root, self.SFX_RESOURCE_FILE))
        )
        self.can: Sequence[tuple[Action, CanData]] = self.tr_can_open(directory=directory)
        self.heights: HeightsParser = HeightsParser.from_file(
            get_path_case_insensitive(directory, Path(directory, "HEIGHTS.SIM"))
        )
        self.resources: dict[int, Resource] = {}
        self.sfx_resources: dict[str, Resource] = {}
        self.light_glows: dict[int, LightAttributes] = {}
        self.mirrored: bool = mirrored
        self.night: bool = night
        self.weather: bool = weather
        self.name: str = directory.name.upper()
        self.game_root: Path = game_root

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
                path = Path(directory, f"{prefix}{variant}{postfix}")
                path = get_path_case_insensitive(directory, path)
                return constructor(path)
        raise FileNotFoundError(f"File {prefix}{postfix} or its variants not found")

    @classmethod
    def tr_can_open(cls, directory: Path) -> Sequence[tuple[Action, CanData]]:
        data = [
            (
                action,
                CanData.from_file(get_path_case_insensitive(directory, Path(directory, filename))),
            )
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
        return replace(obj, actions=object_actions)

    @classmethod
    def _select_wall_edge_idx(cls, polygon: CollisionPolygon) -> Sequence[tuple[int, int]]:
        face = polygon.face
        edges: list[tuple[int, int]] = []
        if Edge.FRONT in polygon.edges and face[0] != face[1]:
            edges.append((face[1], face[0]))
        if Edge.LEFT in polygon.edges and face[1] != face[2]:
            edges.append((face[2], face[1]))
        if Edge.BACK in polygon.edges and face[2] != face[3]:
            edges.append((face[3], face[2]))
        if Edge.RIGHT in polygon.edges and face[3] != face[0]:
            edges.append((face[0], face[3]))
        return edges

    @classmethod
    def _get_wall_edge_idx(cls, polygon: CollisionPolygon) -> Iterable[tuple[int, int]]:
        return cls._select_wall_edge_idx(polygon)

    @classmethod
    def _raise_vertex(cls, heights: Sequence[tuple[Vector3d, float]], vertex: Vertex) -> Vertex:
        def sort_key(vertex: Vertex, x: tuple[Vector3d, float]) -> float:
            location, _ = x
            diff = vertex.location.subtract(location)
            return diff.magnitude()

        def get_height(x: tuple[Vector3d, float]) -> float:
            _, height = x
            return height

        sorted_heights = sorted(heights, key=partial(sort_key, vertex))
        closest_heights = take(3, sorted_heights)
        target_height = min(closest_heights, key=get_height)
        location = vertex.location
        y = location.y + get_height(target_height)
        new_location = location._replace(y=y)
        return replace(vertex, location=new_location)

    @classmethod
    def _make_polygon_wall(
        cls, heights: Sequence[tuple[Vector3d, float]], mesh: CollisionMesh
    ) -> CollisionMesh | None:
        polygons = filter(lambda x: x.has_wall_collision and x.edges, mesh.polygons)
        edges = [cls._get_wall_edge_idx(polygon) for polygon in polygons]
        vertices = mesh.vertices
        edge_vertex_idx = list(frozenset(collapse(edges)))
        vertex_idx_remapping = {idx: (i + len(vertices)) for i, idx in enumerate(edge_vertex_idx)}
        edge_vertices = [vertices[idx] for idx in edge_vertex_idx]
        raised_vertices = [cls._raise_vertex(heights, vertex) for vertex in edge_vertices]

        def make_polygon(edge: tuple[int, int]) -> CollisionPolygon:
            a, b = edge
            c = vertex_idx_remapping[b]
            d = vertex_idx_remapping[a]
            face = (a, b, c, d)
            return CollisionPolygon(face=face)

        vertices = vertices + raised_vertices  # type: ignore[operator]
        wall_polygons = [make_polygon(edge) for edge in collapse(edges, base_type=tuple)]
        if not wall_polygons:
            return None
        mesh = CollisionMesh(vertices=vertices, polygons=wall_polygons)
        return remove_unused_vertices(mesh)

    @classmethod
    def _make_walls(
        cls, heights: Sequence[tuple[Vector3d, float]], segment: TrackSegment
    ) -> CollisionMesh:
        walls = map(lambda x: cls._make_polygon_wall(heights, x), segment.collision_meshes)
        filtered = filter(lambda x: x is not None, walls)
        return reduce(merge_mesh, filtered)  # type: ignore[return-value]

    @classmethod
    def _finalize_segment(
        cls, heights: Iterable[tuple[Vector3d, float]], segment: TrackSegment
    ) -> TrackSegment:
        heights = list(heights)
        floor = segment.collision_meshes
        wall = cls._make_walls(heights=heights, segment=segment)
        collision_meshes = floor + [wall]  # type: ignore[operator]
        return replace(segment, collision_meshes=collision_meshes)

    @classmethod
    def _make_waypoint_height_pair(
        cls,
        first: tuple[Iterable[Vector3d], Iterable[float]],
        middle: tuple[Iterable[Vector3d], Iterable[float]],
        last: tuple[Iterable[Vector3d], Iterable[float]],
    ) -> Iterable[tuple[Vector3d, float]]:
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

    def _make_light(self, stub: LightStub) -> TrackLight:
        attributes = self.light_glows[stub.glow_id]
        return TrackLight(
            location=stub.location,
            color=attributes.color,
            blink_interval_ms=attributes.blink_interval_ms,
            flare_size=attributes.flare_size,
        )

    @property
    def lights(self) -> Iterator[TrackLight]:
        if not self.light_glows:
            for attribute in self.ini.glows:
                self.light_glows[attribute.identifier] = attribute
        return map(self._make_light, self.frd.light_dummies)

    @property
    def directional_light(self) -> DirectionalLight | None:
        sun = self.ini.sun
        sun_resource = self._sun_resource
        if sun is None and sun_resource:
            sun = sun_resource.sun_attributes
        if sun:
            # Angles in INI are in turns. Turns are converted to radians here.
            # The INI angleRho value is not really a spherical coordinate.
            # Some approximations are done here to convert to spherical coordinates.
            rho = sun.angle_rho * tau
            z = self.SUN_DISTANCE * cos(rho)
            phi = atan2(z, self.SUN_DISTANCE)
            theta = sun.angle_theta * tau
            return DirectionalLight(
                phi=phi,
                theta=theta,
                radius=sun.radius,
                resource=sun_resource,
                additive=sun.additive,
                in_front=sun.in_front,
                rotates=sun.rotates,
            )
        return None

    @property
    def cameras(self) -> Iterable[Camera]:
        return self.cam.cameras

    @property
    def ambient_color(self) -> Color:
        return self.ini.ambient_color

    @property
    def horizon(self) -> Horizon:
        return self.ini.horizon

    @property
    def sky_images(self) -> Iterable[Resource]:
        weather = "W" if self.weather else "C"
        night = "N" if self.night else "D"
        return filter(lambda x: fnmatch(x.name, f"H{night}{weather}?"), self.sky.resources)

    @property
    def _sun_resource(self) -> Resource:
        match (self.night, self.weather):
            case (False, False):
                name = "SUND"
            case (True, False):
                name = "SUNN"
            case (False, True):
                name = "SUNW"
            case (True, True):
                name = "SUNW"
        return one(filter(lambda x: x.name == name, self.sky.resources))

    @property
    def clouds(self) -> Resource:
        weather = "W" if self.weather else "D"
        night = "N" if self.night else "D"
        return one(filter(lambda x: x.name == f"CL{weather}{night}", self.sky.resources))

    @classmethod
    def _make_audio_source(cls, bnk: BnkData, dummy: SoundStub) -> AudioSource | None:
        try:
            patch_map = dict(bnk.sound_streams)
            stream = patch_map[dummy.patch]
            return AudioSource(streams=stream, location=dummy.location)
        except KeyError as e:
            logger.exception(e)
            return None

    @property
    def audio_sources(self) -> Iterable[AudioSource]:
        track_name = self.name
        audio_id = self.AUDIO_MAPPING[track_name]
        audio_path = Path(self.game_root, self.AUDIO_DATA_PATH)
        audio_path = get_path_case_insensitive(self.game_root, audio_path)
        audio_file = self.tr_open(
            constructor=BnkData.from_file,
            directory=audio_path,
            prefix=f"TRAM{audio_id:02}",
            postfix=".BNK",
            mirrored=self.mirrored,
            night=self.night,
            weather=self.weather,
        )
        return filter_map(partial(self._make_audio_source, audio_file), self.frd.sound_dummies)
