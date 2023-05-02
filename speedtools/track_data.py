#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Iterator
from pathlib import Path

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
    Vector3d,
)

logger = logging.getLogger(__name__)


class TrackData:
    def __init__(self, directory: Path) -> None:
        logger.debug(f"Opening directory {directory}")
        self.frd: FrdData = FrdData.from_file(Path(directory, "TR.FRD"))
        self.qfs: QfsData = QfsData.from_file(Path(directory, "TR0.QFS"))
        self.sky: QfsData = QfsData.from_file(Path(directory, "SKY.QFS"))
        self.ini: TrackIni = TrackIni.from_file(Path(directory, "TR.INI"))
        self.resources: dict[int, Resource] = {}
        self.light_glows: dict[int, LightAttributes] = {}

    @property
    def objects(self) -> Iterator[TrackObject]:
        return self.frd.objects

    @property
    def track_segments(self) -> Iterator[TrackSegment]:
        return self.frd.track_segments

    @property
    def track_resources(self) -> Iterator[Resource]:
        return self.qfs.resources

    def get_polygon_material(self, polygon: Polygon) -> Resource:
        if not self.resources:
            for index, resource in enumerate(
                filter(lambda resource: not resource.mirrored, self.qfs.resources)
            ):
                self.resources[index] = resource
        return self.resources[polygon.material]

    def _make_light(self, stub: LightStub) -> Light:
        attributes = self.light_glows[stub.glow_id]
        return Light(location=stub.location, attributes=attributes)

    @property
    def lights(self) -> Iterator[Light]:
        if not self.light_glows:
            for attribute in self.ini.glows:
                self.light_glows[attribute.id] = attribute
        return map(self._make_light, self.frd.light_dummies)
