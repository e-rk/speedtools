#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import suppress
from functools import partial
from math import atan2, cos, tau
from pathlib import Path
from typing import TypeVar

from speedtools.cam_data import CamData
from speedtools.can_data import CanData
from speedtools.frd_data import FrdData
from speedtools.fsh_data import FshData
from speedtools.tr_ini import TrackIni
from speedtools.types import (
    Action,
    AnimationAction,
    Camera,
    CollisionType,
    Color,
    DirectionalLight,
    Horizon,
    Light,
    LightAttributes,
    LightStub,
    Polygon,
    Resource,
    TrackObject,
    TrackSegment,
)
from speedtools.utils import unique_named_resources

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

    @property
    def objects(self) -> Iterator[TrackObject]:
        actions = [AnimationAction(action, can.animation) for action, can in self.can]
        return map(partial(self._finalize_object, actions), self.frd.objects)

    @property
    def track_segments(self) -> Iterator[TrackSegment]:
        return self.frd.track_segments

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
