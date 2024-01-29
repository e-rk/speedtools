#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Sequence
from pathlib import Path
from fnmatch import fnmatch

import click

from speedtools.fsh_data import FshData
from speedtools.utils import export_resource, unique_named_resources, create_pil_image

logger = logging.getLogger()
logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
logger.addHandler(sh)


@click.group()
def main():
    pass

@main.command()
@click.option("--output", help="Output directory", type=click.Path(path_type=Path))
@click.argument("files", type=click.Path(path_type=Path), nargs=-1)
def unpack(output: Path | None, files: Sequence[Path]) -> None:
    for file in files:
        logger.info(f"Unpacking: {file}")
        out = Path(file.stem) if output is None else output
        data = FshData.from_file(file)
        resources = unique_named_resources(data.resources)
        export_resource(resources, directory=out)

@main.group()
@click.argument("path", type=click.Path(path_type=Path))
@click.pass_context
def track(ctx, path: Path):
    ctx.ensure_object(dict)
    ctx.obj["path"] = path

@track.group()
@click.pass_context
def sky(ctx):
    pass

@sky.command()
@click.pass_context
@click.option("--output", help="Output file", type=click.Path(path_type=Path))
def cubemap(ctx, output: Path | None):
    sky_path = Path(ctx.obj["path"], "SKY.QFS")
    logger.info(f"Sky resource file: {sky_path}")
    data = FshData.from_file(sky_path)
    resources = filter(lambda x: fnmatch(x.name, "HDC?"), data.resources)
    first_resource = next(resources)
    first_image = create_pil_image(first_resource.image)
    for resource in resources:
        logger.info(resource.name)
        image = create_pil_image(resource.image)
        first_image = first_image.resize((first_image.width + image.width, first_image.height))
        logger.info(first_image.width)
        first_image.paste(image, (first_image.width, 0))
        first_image.save("test.png")
