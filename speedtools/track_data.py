#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Callable, Iterator
from contextlib import suppress
from pathlib import Path
from typing import TypeVar

from speedtools.frd_data import FrdData
from speedtools.qfs_data import QfsData
from speedtools.tr_ini import TrackIni
from speedtools.types import (
    Light,
    LightAttributes,
    LightStub,
    Polygon,
    Resource,
    TrackObject,
    TrackSegment,
)
from speedtools.utils import count_repeats_and_map

logger = logging.getLogger(__name__)
T = TypeVar("T")


class TrackData:
    def __init__(
        self, directory: Path, mirrored: bool = False, night: bool = False, weather: bool = False
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
        self.qfs: QfsData = self.tr_open(
            constructor=QfsData.from_file,
            directory=directory,
            prefix="TR",
            postfix="0.QFS",
            mirrored=mirrored,
            night=night,
            weather=weather,
        )
        self.sky: QfsData = self.tr_open(
            constructor=QfsData.from_file,
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
        self.resources: dict[int, Resource] = {}
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

    @property
    def objects(self) -> Iterator[TrackObject]:
        return self.frd.objects

    @property
    def track_segments(self) -> Iterator[TrackSegment]:
        return self.frd.track_segments

    @property
    def track_resources(self) -> Iterator[Resource]:
        return self.qfs.resources

    @classmethod
    def _make_unique_resource_name(cls, resource: Resource, repeats: int) -> Resource:
        if repeats == 0:
            return resource
        return Resource(
            name=f"{resource.name}-{repeats}",
            image=resource.image,
            mirrored=resource.mirrored,
            nonmirrored=resource.nonmirrored,
            additive=resource.additive,
        )

    def _init_resources(self) -> None:
        if self.mirrored:
            resources = filter(lambda resource: not resource.nonmirrored, self.qfs.resources)
        else:
            resources = filter(lambda resource: not resource.mirrored, self.qfs.resources)
        unique_named_resources = count_repeats_and_map(
            iterable=resources, func=self._make_unique_resource_name, key=lambda x: x.name
        )
        self.resources = dict(enumerate(unique_named_resources))

    def get_polygon_material(self, polygon: Polygon) -> Resource:
        if not self.resources:
            self._init_resources()
        return self.resources[polygon.material]

    def _make_light(self, stub: LightStub) -> Light:
        attributes = self.light_glows[stub.glow_id]
        return Light(location=stub.location, attributes=attributes)

    @property
    def lights(self) -> Iterator[Light]:
        if not self.light_glows:
            for attribute in self.ini.glows:
                self.light_glows[attribute.identifier] = attribute
        return map(self._make_light, self.frd.light_dummies)
