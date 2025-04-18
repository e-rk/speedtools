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

from parse import parse, search  # type: ignore[import-untyped]

from speedtools.types import Color, Horizon, LightAttributes, SunAttributes

logger = logging.getLogger(__name__)


class TrackIni:
    def __init__(self, parser: ConfigParser) -> None:
        self.parser = parser

    @classmethod
    def from_file(cls, path: Path) -> TrackIni:
        parser = ConfigParser()
        with open(path, "r", encoding="utf-8") as file:
            parser.read_file(file)
        return cls(parser=parser)

    @classmethod
    def _make_glow(cls, name: str, string: str) -> LightAttributes:
        no_spaces = string.replace(" ", "")
        results = search("[{:d},{:d},{:d},{:d}],{:d},{:d},{:d},{:f}", no_spaces)
        (identifier,) = parse("glow{:d}", name)
        alpha, red, green, blue, is_blinking, interval, _, flare_size = results
        color = Color(alpha=alpha, red=red, green=green, blue=blue)
        blink_interval = interval if is_blinking == 1 else None
        return LightAttributes(
            identifier=identifier,
            color=color,
            blink_interval_ms=blink_interval,
            flare_size=flare_size,
        )

    @classmethod
    def _parse_color(cls, value: str) -> Color:
        red, green, blue = parse("[{:d},{:d},{:d}]", value)
        return Color(alpha=255, red=red, green=green, blue=blue)

    @property
    def glows(self) -> Iterator[LightAttributes]:
        return starmap(self._make_glow, self.parser["track glows"].items())

    @property
    def sun(self) -> SunAttributes | None:
        try:
            sun = self.parser["sun"]
            if sun["hasSun"] == "0":
                return None
            return SunAttributes(
                angle_theta=float(sun["angleTheta"]),
                angle_rho=float(sun["angleRho"]),
                radius=float(sun["radius"]),
                rotates=sun.get("rotates", "0") != "0",
                additive=sun.get("additive", "0") != "0",
                in_front=sun.get("inFront", "0") != "0",
            )
        except KeyError:
            return None

    @property
    def ambient_color(self) -> Color:
        light = self.parser["light"]
        red = int(light["AmbientRed"])
        green = int(light["AmbientGreen"])
        blue = int(light["AmbientBlue"])
        red = (red * 255) // 100
        green = (green * 255) // 100
        blue = (blue * 255) // 100
        return Color(alpha=255, red=red, green=green, blue=blue)

    @property
    def horizon(self) -> Horizon:
        strip = self.parser["strip"]
        sun_side = self._parse_color(strip["hrzSunColor"])
        top_side = self._parse_color(strip["hrzSkyTopColor"])
        opposite_side = self._parse_color(strip["hrzOppositeSunColor"])
        earth_bottom = opposite_side = self._parse_color(strip["hrzEarthBotColor"])
        earth_top = opposite_side = self._parse_color(strip["hrzEarthTopColor"])
        return Horizon(
            sun_side=sun_side,
            sun_top_side=top_side,
            sun_opposite_side=opposite_side,
            earth_bottom=earth_bottom,
            earth_top=earth_top,
        )
