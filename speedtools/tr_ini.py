#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from collections.abc import Iterator
from configparser import ConfigParser
from functools import partial
from itertools import starmap
from pathlib import Path

from parse import parse, search  # type: ignore[import-untyped]

from speedtools.types import (
    CloudAttributes,
    Color,
    FogAttributes,
    Horizon,
    LightAttributes,
    LightningAttributes,
    SunAttributes,
    WeatherAttributes,
    WeatherType,
)

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
        return Horizon(
            sun_side=self._parse_color(strip["hrzSunColor"]),
            sun_top_side=self._parse_color(strip["hrzSkyTopColor"]),
            sun_opposite_side=self._parse_color(strip["hrzOppositeSunColor"]),
            earth_bottom=self._parse_color(strip["hrzEarthBotColor"]),
            earth_top=self._parse_color(strip["hrzEarthTopColor"]),
            mirror=strip.getint("hrzMirror", 0) != 0,
            has_panorama=strip.getint("hrzHasPMX", 0) != 0,
            bottom_y=strip.getfloat("hrzBottomYOff", 0.0),
            gouraud_middle=strip.getfloat("hrzGouraudMiddle", 0.0),
            gouraud_height=strip.getfloat("hrzGouraudHeight", 0.0),
            panorama_bottom=strip.getfloat("hrzPmxBottom", 0.0),
            panorama_top=strip.getfloat("hrzPmxTop", 0.0),
            radius=strip.getfloat("hrzfRadius", 0.0),
            angle=strip.getfloat("hrzAngle", 0.0) % 1.0,
        )

    @property
    def clouds(self) -> CloudAttributes:
        get_int = partial(self.parser.getint, "clouds", fallback=0)
        get_float = partial(self.parser.getfloat, "clouds", fallback=0.0)
        bright = get_int("cloudBright")
        return CloudAttributes(
            cloud_type=get_int("cloudType"),
            bright=bright,
            variance=min(get_int("cloudVariance"), bright),
            nimbus=get_float("cloudNimbus"),
            fog=get_int("cloudFog") != 0,
            visual_height=get_int("cloudVisualHeight"),
            wind_speed=get_int("windSpeed"),
            wind_direction=get_int("windDir"),
            y_offset=get_float("cloudYOffset"),
            height=get_float("cloudHeight"),
            u_scale=get_float("cloudUscale") or 1.0,
            v_scale=get_float("cloudVscale") or 1.0,
        )

    @property
    def lightning(self) -> LightningAttributes:
        get_int = partial(self.parser.getint, "lightning", fallback=0)
        return LightningAttributes(
            chance=get_int("lightningChance"),
            off_ticks=get_int("lightningOffTicks"),
        )

    @property
    def weather(self) -> WeatherAttributes:
        get_int = partial(self.parser.getint, "weather", fallback=0)
        return WeatherAttributes(
            weather_type=WeatherType(get_int("type")),
            start_slice=get_int("startSlice"),
            end_slice=get_int("endSlice"),
            fade=get_int("fade"),
            stay_time_on=get_int("stayTimeOn"),
            fade_time_off=get_int("fadeTimeOff"),
            stay_time_off=get_int("stayTimeOff"),
            fade_time_on=get_int("fadeTimeOn"),
            density=get_int("denstiy", fallback=100),
        )

    @property
    def fog(self) -> FogAttributes:
        color = self.parser.get("fog", "fogColor", fallback="[0,0,0]")
        return FogAttributes(
            color=self._parse_color(color),
            density=self.parser.getint("fog", "fogDensity", fallback=0),
            horizon=self.parser.getfloat("fog", "fogHorizon", fallback=0.0),
        )
