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
from speedtools.types import Bitmap, BlendMode, FshDataType, Resource

logger = logging.getLogger(__name__)


class FshData:
    def __init__(self, fsh_parser: FshParser) -> None:
        self.fsh = fsh_parser

    @classmethod
    def from_file(cls, filename: Path) -> FshData:
        suffix = filename.suffix.lower()
        if suffix == ".qfs":
            parser = QfsParser.from_file(filename=filename).data
        elif suffix == ".fsh":
            parser = FshParser.from_file(filename=filename)
        else:
            raise ValueError("Invalid fsh file extension")
        return cls(fsh_parser=parser)

    @classmethod
    def _get_data_by_code(
        cls, codes: Container[FshDataType], resource: FshParser.DataBlock
    ) -> Iterator[FshParser.DataBlock]:
        return filter(lambda x: x.code in codes, resource.body.blocks)

    @classmethod
    def _make_bitmap(cls, resource: FshParser.Resource) -> tuple[Bitmap, FshDataType]:
        bitmap = one(
            cls._get_data_by_code(
                codes=(
                    FshDataType.bitmap8,
                    FshDataType.bitmap32,
                    FshDataType.bitmap16,
                    FshDataType.bitmap16_alpha,
                ),
                resource=resource,
            )
        )
        bitmap_type = bitmap.code
        if bitmap_type is FshDataType.bitmap8:
            palette = one(cls._get_data_by_code(codes=[FshDataType.palette], resource=resource))
            palette_colors = [element.color for element in palette.data.data]
            rgba_int = [palette_colors[element] for element in bitmap.data.data]
            rgba_bytes = pack(f"<{len(rgba_int)}I", *rgba_int)
            bitmap_object = Bitmap(
                width=bitmap.width,
                height=bitmap.height,
                data=rgba_bytes,
            )
        elif bitmap_type in (
            FshDataType.bitmap32,
            FshDataType.bitmap16,
            FshDataType.bitmap16_alpha,
        ):
            rgba_int = [elem.color for elem in bitmap.data.data]
            rgba_bytes = pack(f"<{len(rgba_int)}I", *rgba_int)
            bitmap_object = Bitmap(
                width=bitmap.width,
                height=bitmap.height,
                data=rgba_bytes,
            )
        else:
            raise RuntimeError("Bitmap resource not recognized")
        return bitmap_object, bitmap_type

    @classmethod
    def _make_resource(cls, resource: FshParser.Resource) -> Resource:
        bitmap, bitmap_type = cls._make_bitmap(resource)
        is_32bit = bitmap_type is FshDataType.bitmap32
        text = only(cls._get_data_by_code(codes=[FshDataType.text], resource=resource))
        text_data = text.data if text is not None else None
        mirrored = "<mirrored>" in text_data if text_data is not None else False
        nonmirrored = "<nonmirrored>" in text_data if text_data is not None else False
        additive = "<additive>" in text_data if text_data is not None else False
        blend_mode = None
        if is_32bit:
            blend_mode = BlendMode.ALPHA
        elif additive:
            blend_mode = BlendMode.ADDITIVE
        return Resource(
            name=resource.name,
            image=bitmap,
            mirrored=mirrored,
            nonmirrored=nonmirrored,
            blend_mode=blend_mode,
        )

    @property
    def resources(self) -> Iterator[Resource]:
        return map(self._make_resource, self.fsh.resources)
