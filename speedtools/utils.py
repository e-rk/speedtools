#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
import os
from collections.abc import Iterable, Iterator
from contextlib import suppress
from functools import singledispatch
from io import BytesIO
from itertools import islice
from pathlib import Path
from typing import Any, TypeVar

from PIL import Image as pil_Image

from speedtools.types import Bitmap, Image, Resource

logger = logging.getLogger(__name__)

T = TypeVar("T")


def islicen(iterable: Iterable[T], start: int, num: int) -> Iterable[T]:
    return islice(iterable, start, start + num)


@singledispatch
def create_pil_image(image: Image) -> Any:
    buffer = BytesIO(image.data)
    return pil_Image.open(fp=buffer)


@create_pil_image.register
def _(image: Bitmap) -> Any:
    return pil_Image.frombytes("RGBA", (image.width, image.height), data=image.data)


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
    output_file = Path(dir, f"{resource.name}.png")
    image = create_pil_image(resource.image)
    logger.info(f"Writing image: {output_file}")
    image.save(output_file)
