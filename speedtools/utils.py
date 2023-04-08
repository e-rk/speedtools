#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
import os
from collections.abc import Callable, Iterable
from contextlib import suppress
from pathlib import Path
from typing import Any

from PIL import Image

from speedtools.types import Resource

logger = logging.getLogger(__name__)


def _default_resource_filename(index: int, resource: Resource, *args: Any) -> str:
    return str(index).zfill(4)


def write_resources(
    resources: Iterable[Resource],
    output_dir: Path,
    filename_func: Callable[..., str] = _default_resource_filename,
    *args: Any,
) -> None:
    with suppress(FileExistsError):
        os.makedirs(output_dir)
    for index, (resource, *other) in enumerate(zip(resources, *args, strict=True)):
        name = filename_func(index=index, resource=resource, *other)
        bitmap = resource.bitmap
        output_file = Path(output_dir, f"{name}.png")
        logger.info(f"Writing image: {output_file}")
        image = Image.frombytes("RGBA", (bitmap.width, bitmap.height), data=bitmap.rgba)
        image.save(output_file)
