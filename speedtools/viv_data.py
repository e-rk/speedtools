#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Literal, TypeAlias, overload

from more_itertools import one

from speedtools.parsers import BnkParser, CtbParser, FceParser, FedataParser, VivParser

logger = logging.getLogger(__name__)

EntryTypes: TypeAlias = FceParser | FedataParser | BnkParser | CtbParser | str | bytes


class Entry(Enum):
    Performance = ("carp.txt", str)
    CarBody = ("car.fce", FceParser)
    CarInterior = ("dash.fce", FceParser)
    HelicopterBody = ("hel.fce", FceParser)
    CarengCtb = ("careng.ctb", CtbParser)
    CarengLtb = ("careng.ltb", CtbParser)
    CarengBnk = ("careng.bnk", BnkParser)
    OCarengBnk = ("ocareng.bnk", BnkParser)
    SCarengBnk = ("scareng.bnk", BnkParser)
    CarBodyTexture = ("car00.tga", bytes)
    CarInteriorTexture = ("dash00.tga", bytes)
    FedataEng = ("fedata.eng", FedataParser)
    FedataGer = ("fedata.ger", FedataParser)
    FedataSpa = ("fedata.spa", FedataParser)
    FedataIta = ("fedata.ita", FedataParser)
    FedataSwe = ("fedata.swe", FedataParser)
    FedataJap = ("fedata.jap", FedataParser)
    FedataFre = ("fedata.fre", FedataParser)

    @property
    def filename(self) -> str:
        name, _ = self.value
        return name  # type: ignore[no-any-return]


FedataType = Literal[
    Entry.FedataEng,
    Entry.FedataGer,
    Entry.FedataIta,
    Entry.FedataJap,
    Entry.FedataSpa,
    Entry.FedataSwe,
    Entry.FedataFre,
]


class VivData:
    def __init__(self, parser: VivParser) -> None:
        self.viv: VivParser = parser

    @classmethod
    def from_file(cls, path: Path) -> VivData:
        parser = VivParser.from_file(path)
        return cls(parser=parser)

    @overload
    def get(self, entry: Literal[Entry.Performance]) -> str: ...
    @overload
    def get(
        self, entry: Literal[Entry.CarBody, Entry.CarInterior, Entry.HelicopterBody]
    ) -> FceParser: ...
    @overload
    def get(self, entry: Literal[Entry.CarengCtb, Entry.CarengLtb]) -> CtbParser: ...
    @overload
    def get(
        self, entry: Literal[Entry.CarengBnk, Entry.OCarengBnk, Entry.SCarengBnk]
    ) -> BnkParser: ...
    @overload
    def get(self, entry: Literal[Entry.CarBodyTexture, Entry.CarInteriorTexture]) -> bytes: ...
    @overload
    def get(self, entry: FedataType) -> FedataParser: ...

    def get(self, entry: Entry) -> EntryTypes:
        name, expected_type = entry.value
        try:
            viv_entry = one(filter(lambda x: x.name == name, self.viv.entries))
            if not isinstance(viv_entry.body, expected_type):
                raise TypeError(f"Unexpected VIV entry type: {expected_type}")
            return viv_entry.body
        except ValueError as e:
            raise FileNotFoundError from e
