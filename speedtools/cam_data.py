#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from pathlib import Path

from more_itertools import chunked, strictly_n, transpose

from speedtools.parsers import CamParser
from speedtools.types import Camera, Matrix3x3, Vector3d

logger = logging.getLogger(__name__)


class CamData:
    def __init__(self, parser: CamParser) -> None:
        self.cam = parser

    @classmethod
    def from_file(cls, path: Path) -> CamData:
        parser = CamParser.from_file(path)
        return cls(parser)

    @classmethod
    def _make_matrix(cls, value: Sequence[float]) -> Matrix3x3:
        val = list(strictly_n(value, 9))
        rows = [Vector3d(x=x, y=y, z=z) for x, y, z in transpose(chunked(val, 3, strict=True))]
        return Matrix3x3(x=rows[0], y=rows[1], z=rows[2])

    @classmethod
    def _make_camera(cls, camera: CamParser.Camera) -> Camera:
        location = Vector3d(x=camera.location.x, y=camera.location.y, z=camera.location.z)
        transform = cls._make_matrix(camera.transform)
        return Camera(location=location, transform=transform)

    @property
    def cameras(self) -> Iterable[Camera]:
        return map(self._make_camera, self.cam.cameras)
