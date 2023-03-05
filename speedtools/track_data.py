#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from itertools import chain
from pathlib import Path

from speedtools.frd_data import FrdData
from speedtools.qfs_data import QfsData

logger = logging.getLogger(__name__)


class TrackData:
    def __init__(self, directory):
        logger.debug(f"Opening directory {directory}")
        self.frd = FrdData.from_file(Path(directory, "TR.FRD"))
        self.qfs = QfsData.from_file(Path(directory, "TR0.QFS"))
        self.sky = QfsData.from_file(Path(directory, "SKY.QFS"))

    @property
    def objects(self):
        return self.frd.objects

    @property
    def track_segments(self):
        return self.frd.track_segments

    @property
    def material_ids(self):
        materials = set()
        for object in chain(self.track_segments, self.objects):
            for polygon in object.polygons:
                materials.add(polygon.material)
        return materials

    def get_material(self, material_id):
        pass

    @property
    def track_bitmaps(self):
        return self.qfs.raw_bitmaps
