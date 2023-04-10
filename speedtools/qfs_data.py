#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Iterator
from struct import pack
from typing import Container

from speedtools.parsers import FshParser, QfsParser
from speedtools.types import Bitmap, FshDataType, Resource

logger = logging.getLogger(__name__)


class QfsData(QfsParser):
    def _get_data_by_code(
        self, codes: Container[FshDataType], resource: FshParser.DataBlock
    ) -> FshParser.DataBlock:
        return next(  # type: ignore[no-any-return]
            filter(lambda x: x.code in codes, resource.body.blocks)
        )

    def _make_bitmap(self, resource: FshParser.Resource) -> Bitmap:
        bitmap = self._get_data_by_code(
            codes=[FshDataType.bitmap8, FshDataType.bitmap32], resource=resource
        )
        if bitmap.code is FshDataType.bitmap8:
            palette = self._get_data_by_code(codes=[FshDataType.palette], resource=resource)
            palette_colors = [element.color for element in palette.data.data]
            rgba_int = [palette_colors[element] for element in bitmap.data.data]
            rgba_bytes = pack(f"<{len(rgba_int)}I", *rgba_int)
            bitmap_object = Bitmap(
                width=bitmap.width,
                height=bitmap.height,
                rgba=rgba_bytes,
            )
        elif bitmap.code is FshDataType.bitmap32:
            rgba_int = [elem.color for elem in bitmap.data.data]
            rgba_bytes = pack(f"<{len(rgba_int)}I", *rgba_int)
            bitmap_object = Bitmap(
                width=bitmap.width,
                height=bitmap.height,
                rgba=rgba_bytes,
            )
        else:
            raise RuntimeError("Bitmap resource not recognized")
        return bitmap_object

    @property
    def raw_bitmaps(self) -> Iterator[Bitmap]:
        for resource in self.data.resources:
            yield self._make_bitmap(resource)

    @property
    def resources(self) -> Iterator[Resource]:
        for resource in self.data.resources:
            bitmap = self._make_bitmap(resource)
            text = self._get_data_by_code(codes=[FshDataType.text], resource=resource)
            text_data = text.data if text is not None else None
            mirrored = "<mirrored>" == text_data if text_data is not None else False
            # if not mirrored:
            #     mirrored = "<nonmirrored>" == text_data if text_data is not None else False
            additive = False
            yield Resource(
                name=resource.name,
                bitmap=bitmap,
                text=text_data,
                mirrored=mirrored,
                additive=additive,
            )
