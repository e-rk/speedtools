#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Iterator
from itertools import chain
from pathlib import Path

from speedtools.frd_data import FrdData
from speedtools.qfs_data import QfsData
from speedtools.types import Bitmap, Resource, TrackObject, TrackSegment

logger = logging.getLogger(__name__)


class TrackData:
    def __init__(self, directory: Path) -> None:
        logger.debug(f"Opening directory {directory}")
        self.frd: FrdData = FrdData.from_file(Path(directory, "TR.FRD"))
        self.qfs: QfsData = QfsData.from_file(Path(directory, "TR0.QFS"))
        self.sky: QfsData = QfsData.from_file(Path(directory, "SKY.QFS"))

    @property
    def objects(self) -> Iterator[TrackObject]:
        return self.frd.objects

    @property
    def track_segments(self) -> Iterator[TrackSegment]:
        return self.frd.track_segments

    @property
    def material_ids(self) -> set[str]:
        materials = set()
        for object in chain(self.track_segments, self.objects):
            for polygon in object.polygons:
                materials.add(polygon.material)
        return materials

    @property
    def track_resources(self) -> Iterator[Resource]:
        return self.qfs.resources

    @property
    def track_bitmaps(self) -> Iterator[Bitmap]:
        return self.qfs.raw_bitmaps
