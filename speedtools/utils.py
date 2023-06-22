#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
import os
from collections.abc import Callable, Hashable, Iterable, Iterator
from contextlib import suppress
from functools import singledispatch
from io import BytesIO
from itertools import islice
from pathlib import Path
from typing import Any, Dict, TypeVar

from PIL import Image as pil_Image

from speedtools.types import Bitmap, Image, Resource

logger = logging.getLogger(__name__)

T = TypeVar("T")
Ty = TypeVar("Ty")


def islicen(iterable: Iterable[T], start: int, num: int) -> Iterable[T]:
    return islice(iterable, start, start + num)


def count_repeats_and_map(
    iterable: Iterable[T], func: Callable[[T, int], Ty], key: Callable[[T], Hashable]
) -> Iterable[Ty]:
    count: Dict[Hashable, int] = {}
    for item in iterable:
        k = key(item)
        count[k] = count.setdefault(k, -1) + 1
        yield func(item, count[k])


@singledispatch
def create_pil_image(image: Image) -> Any:
    buffer = BytesIO(image.data)
    return pil_Image.open(fp=buffer)


@create_pil_image.register
def _(image: Bitmap) -> Any:
    return pil_Image.frombytes("RGBA", (image.width, image.height), data=image.data)


@singledispatch
def export_resource(resource: Any, directory: Path) -> None:
    raise NotImplementedError("Unsupported resource type")


@export_resource.register(Iterator)
def _(resource: Iterator[Resource], directory: Path) -> None:
    for res in resource:
        export_resource(res, directory=directory)


@export_resource.register(Resource)
def _(resource: Resource, directory: Path) -> None:
    with suppress(FileExistsError):
        os.makedirs(directory)
    output_file = Path(directory, f"{resource.name}.png")
    image = create_pil_image(resource.image)
    logger.info(f"Writing image: {output_file}")
    image.save(output_file)
