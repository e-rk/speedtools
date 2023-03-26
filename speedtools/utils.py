#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
import os
from contextlib import suppress
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def write_bitmaps(bitmaps, output_dir):
    with suppress(FileExistsError):
        os.makedirs(output_dir)
    for bitmap in bitmaps:
        output_file = Path(output_dir, f"{bitmap.id}.png")
        logger.info(f"Writing image: {output_file}")
        image = Image.frombytes("RGBA", (bitmap.width, bitmap.height), data=bitmap.rgba)
        image.save(output_file)


def _default_resource_filename(index, resource, *args):
    logger.debug(f"Resource: {resource.text}")
    return str(index).zfill(4)
    # return resource.name


# def write_resource(resource, name, directory):


def write_resources(resources, output_dir, filename_func=_default_resource_filename, *args):
    with suppress(FileExistsError):
        os.makedirs(output_dir)
    for index, (resource, *other) in enumerate(zip(resources, *args, strict=True)):
        name = filename_func(index=index, resource=resource, *other)
        bitmap = resource.bitmap
        output_file = Path(output_dir, f"{name}.png")
        logger.info(f"Writing image: {output_file}")
        image = Image.frombytes("RGBA", (bitmap.width, bitmap.height), data=bitmap.rgba)
        image.save(output_file)
