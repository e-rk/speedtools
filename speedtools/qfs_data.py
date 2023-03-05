#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections import namedtuple
from struct import pack

from speedtools.parser.qfs import Qfs

ch = logging.StreamHandler()


class Bitmap(namedtuple("Bitmap", ["id", "width", "height", "rgba"])):
    pass


class QfsData(Qfs):
    @property
    def raw_bitmaps(self):
        for object in self.data.objects:
            if object.body.code is self.data.BitmapCode.bitmap_8:
                palette_colors = [element.color for element in object.aux.data]
                rgba_int = [palette_colors[element] for element in object.body.data]
                rgba_bytes = pack(f"<{len(rgba_int)}I", *rgba_int)
                bitmap = Bitmap(
                    id=object.identifier,
                    width=object.body.width,
                    height=object.body.height,
                    rgba=rgba_bytes,
                )
            elif object.body.code is self.data.BitmapCode.bitmap_32:
                rgba_int = [elem.color for elem in object.body.data]
                rgba_bytes = pack(f"<{len(rgba_int)}I", *rgba_int)
                bitmap = Bitmap(
                    id=object.identifier,
                    width=object.body.width,
                    height=object.body.height,
                    rgba=rgba_bytes,
                )
            yield bitmap

    def get_resource(self, identifier):
        pass
