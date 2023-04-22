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
from speedtools.types import Polygon, Resource, TrackObject, TrackSegment

logger = logging.getLogger(__name__)


class TrackData:
    def __init__(self, directory: Path) -> None:
        logger.debug(f"Opening directory {directory}")
        self.frd: FrdData = FrdData.from_file(Path(directory, "TR.FRD"))
        self.qfs: QfsData = QfsData.from_file(Path(directory, "TR0.QFS"))
        self.sky: QfsData = QfsData.from_file(Path(directory, "SKY.QFS"))
        self.resources: dict[int, Resource] = {}

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
