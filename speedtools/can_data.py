#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from pathlib import Path

from speedtools.parsers import CanParser
from speedtools.types import Animation, Quaternion, Vector3d

logger = logging.getLogger(__name__)


class CanData:
    def __init__(self, parser: CanParser) -> None:
        self.can = parser

    @classmethod
    def from_file(cls, path: Path) -> CanData:
        parser = CanParser.from_file(path)
        return cls(parser)

    @property
    def animation(self) -> Animation:
        can = self.can
        locations = [
            Vector3d(x=keyframe.location.x, y=keyframe.location.y, z=keyframe.location.z)
            for keyframe in self.can.keyframes
        ]
        quaternions = [
            Quaternion(
                x=keyframe.quaternion.x,
                y=keyframe.quaternion.y,
                z=keyframe.quaternion.z,
                w=keyframe.quaternion.w,
            )
            for keyframe in self.can.keyframes
        ]
        return Animation(
            length=can.num_keyframes, delay=can.delay, locations=locations, quaternions=quaternions
        )
