#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from struct import pack
from typing import Container

from more_itertools import one, only

from speedtools.parsers import FshParser, QfsParser
from speedtools.types import Bitmap, FshDataType, Resource

logger = logging.getLogger(__name__)


class QfsData:
    def __init__(self, qfs_parser: QfsParser) -> None:
        self.qfs = qfs_parser

    @classmethod
    def from_file(cls, filename: Path) -> QfsData:
        parser = QfsParser.from_file(filename=filename)
        return cls(qfs_parser=parser)

    @classmethod
    def _get_data_by_code(
        cls, codes: Container[FshDataType], resource: FshParser.DataBlock
    ) -> Iterator[FshParser.DataBlock]:
        return filter(lambda x: x.code in codes, resource.body.blocks)

    @classmethod
    def _make_bitmap(cls, resource: FshParser.Resource) -> Bitmap:
        bitmap = one(
            cls._get_data_by_code(
                codes=[FshDataType.bitmap8, FshDataType.bitmap32], resource=resource
            )
        )
        if bitmap.code is FshDataType.bitmap8:
            palette = one(cls._get_data_by_code(codes=[FshDataType.palette], resource=resource))
            palette_colors = [element.color for element in palette.data.data]
            rgba_int = [palette_colors[element] for element in bitmap.data.data]
            rgba_bytes = pack(f"<{len(rgba_int)}I", *rgba_int)
            bitmap_object = Bitmap(
                width=bitmap.width,
                height=bitmap.height,
                data=rgba_bytes,
            )
        elif bitmap.code is FshDataType.bitmap32:
            rgba_int = [elem.color for elem in bitmap.data.data]
            rgba_bytes = pack(f"<{len(rgba_int)}I", *rgba_int)
            bitmap_object = Bitmap(
                width=bitmap.width,
                height=bitmap.height,
                data=rgba_bytes,
            )
        else:
            raise RuntimeError("Bitmap resource not recognized")
        return bitmap_object

    @classmethod
    def _make_resource(cls, resource: FshParser.Resource) -> Resource:
        bitmap = cls._make_bitmap(resource)
        text = only(cls._get_data_by_code(codes=[FshDataType.text], resource=resource))
        text_data = text.data if text is not None else None
        mirrored = "<mirrored>" in text_data if text_data is not None else False
        nonmirrored = "<nonmirrored>" in text_data if text_data is not None else False
        additive = "<additive>" in text_data if text_data is not None else False
        return Resource(
            name=resource.name,
            image=bitmap,
            mirrored=mirrored,
            nonmirrored=nonmirrored,
            additive=additive,
        )

    @property
    def resources(self) -> Iterator[Resource]:
        return map(self._make_resource, self.qfs.data.resources)
