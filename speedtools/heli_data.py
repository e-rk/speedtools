#
# Copyright (c) 2026 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Iterable

from speedtools.fce_data import FceData
from speedtools.types import (
    Helicopter,
    Image,
    Part,
    Polygon,
    Resource,
    Vector3d,
    VehicleLight,
)
from speedtools.utils import get_path_case_insensitive
from speedtools.viv_data import Entry, VivData

logger = logging.getLogger(__name__)


class HeliData:
    def __init__(self, directory: Path) -> None:
        logger.debug(f"Opening directory {directory}")
        self.directory: Path = directory
        self.viv: VivData = VivData.from_file(
            get_path_case_insensitive(directory, Path(directory, "CAR.VIV"))
        )
        self.fce: FceData = FceData(self.viv.get(Entry.HelicopterBody))

    @property
    def material(self) -> Resource:
        data = self.viv.get(Entry.HelicopterTexture)
        return Resource(name=Entry.HelicopterTexture.filename, image=Image(data=data))

    @property
    def material_map(self) -> Callable[[Polygon], Resource]:
        resource = self.material

        def inner(polygon: Polygon) -> Resource:
            if polygon.material == 0:
                return resource
            raise KeyError(f"Material {polygon.material} not found")

        return inner

    @property
    def parts(self) -> Iterable[Part]:
        return self.fce.parts

    @property
    def lights(self) -> Iterable[VehicleLight]:
        return self.fce.lights

    @property
    def dimensions(self) -> Vector3d:
        return self.fce.dimensions

    @property
    def helicopter(self) -> Helicopter:
        return Helicopter(
            parts=list(self.parts),
            lights=list(self.lights),
            dimensions=self.dimensions,
        )
