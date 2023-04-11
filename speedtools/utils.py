#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
import os
from collections.abc import Iterator
from contextlib import suppress
from functools import singledispatch
from pathlib import Path
from typing import Any

from PIL import Image

from speedtools.types import Resource

logger = logging.getLogger(__name__)


@singledispatch
def export_resource(resource: Any, dir: Path) -> None:
    raise NotImplementedError("Unsupported resource type")


@export_resource.register(Iterator)
def _(resource: Iterator[Resource], dir: Path) -> None:
    for res in resource:
        export_resource(res, dir=dir)


@export_resource.register(Resource)
def _(resource: Resource, dir: Path) -> None:
    with suppress(FileExistsError):
        os.makedirs(dir)
    bitmap = resource.bitmap
    output_file = Path(dir, f"{resource.name}.png")
    logger.info(f"Writing image: {output_file}")
    image = Image.frombytes("RGBA", (bitmap.width, bitmap.height), data=bitmap.rgba)
    image.save(output_file)
