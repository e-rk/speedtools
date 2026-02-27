#
# Copyright (c) 2026 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from kaitaistruct import KaitaiStream  # type: ignore[import-untyped]

from speedtools.parsers import SpdParser

logger = logging.getLogger(__name__)


class SpdData:
    def __init__(self, parser: SpdParser) -> None:
        self.parser = parser

    @classmethod
    def from_file(cls, num_road_blocks: int, path: Path) -> SpdData:
        with open(path, "rb") as file:
            stream = KaitaiStream(file)
            parser = SpdParser(num_road_blocks, stream)
            return cls(parser=parser)

    @property
    def speed(self) -> Sequence[int]:
        return self.parser.speed  # type: ignore[no-any-return]

    @property
    def lane(self) -> Sequence[int]:
        return self.parser.lane  # type: ignore[no-any-return]

    @property
    def offset(self) -> Sequence[float]:
        return self.parser.offset  # type: ignore[no-any-return]
