#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from collections.abc import Iterator
from configparser import ConfigParser
from itertools import starmap
from pathlib import Path

from parse import parse, search

from speedtools.types import Color, LightAttributes

logger = logging.getLogger(__name__)


class TrackIni:
    def __init__(self, parser: ConfigParser) -> None:
        self.parser = parser

    @classmethod
    def from_file(cls, path: Path) -> TrackIni:
        parser = ConfigParser()
        parser.read_file(open(path, "r"))
        return cls(parser=parser)

    @classmethod
    def _make_glow(cls, name: str, string: str) -> LightAttributes:
        no_spaces = string.replace(" ", "")
        results = search("[{:d},{:d},{:d},{:d}],{:d},{:d},{:d},{:f}", no_spaces)
        (id,) = parse("glow{:d}", name)
        alpha, red, green, blue, is_blinking, interval, _, flare_size = results
        color = Color(alpha=alpha, red=red, green=green, blue=blue)
        blink_interval = interval if is_blinking == 1 else None
        return LightAttributes(
            id=id,
            color=color,
            blink_interval_ms=blink_interval,
            flare_size=flare_size,
        )

    @property
    def glows(self) -> Iterator[LightAttributes]:
        return starmap(self._make_glow, self.parser["track glows"].items())
