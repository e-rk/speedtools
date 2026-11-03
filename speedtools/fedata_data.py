#
# Copyright (c) 2026 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from pathlib import Path

from speedtools.parsers import FedataParser
from speedtools.types import CarClass, EngineLocation


class FedataData:
    manufacturer_string = 0
    model_string = 1
    name_string = 2

    car_classes = {
        FedataParser.CarClass.aaa: CarClass.AAA,
        FedataParser.CarClass.aa: CarClass.AA,
        FedataParser.CarClass.a: CarClass.A,
        FedataParser.CarClass.b: CarClass.B,
    }

    engine_locations = {
        FedataParser.EngineLocation.front: EngineLocation.FRONT,
        FedataParser.EngineLocation.mid: EngineLocation.MID,
        FedataParser.EngineLocation.rear: EngineLocation.REAR,
    }

    def __init__(self, parser: FedataParser) -> None:
        self.fedata = parser

    @classmethod
    def from_file(cls, path: Path) -> FedataData:
        return cls(parser=FedataParser.from_file(path))

    @classmethod
    def from_bytes(cls, data: bytes) -> FedataData:
        return cls(parser=FedataParser.from_bytes(data))

    @property
    def serial(self) -> int:
        return self.fedata.serial  # type: ignore[no-any-return]

    @property
    def car_class(self) -> CarClass:
        return self.car_classes.get(self.fedata.car_class, CarClass.NONE)

    @property
    def police(self) -> bool:
        return self.fedata.police  # type: ignore[no-any-return]

    @property
    def engine_location(self) -> EngineLocation:
        return self.engine_locations.get(self.fedata.engine_location, EngineLocation.FRONT)

    def _string(self, index: int) -> str:
        strings = self.fedata.strings
        return strings[index].value if index < len(strings) else ""

    @property
    def manufacturer(self) -> str:
        return self._string(self.manufacturer_string)

    @property
    def model(self) -> str:
        return self._string(self.model_string)

    @property
    def name(self) -> str:
        return self._string(self.name_string)
