#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Sequence
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import click

from speedtools.bnk_data import BnkData
from speedtools.fsh_data import FshData
from speedtools.utils import (
    export_resource,
    make_horizon_texture,
    raw_stream_to_wav,
    unique_named_resources,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
logger.addHandler(sh)


@click.group()
def main() -> None:
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
def track(ctx: Any, path: Path) -> None:
    ctx.ensure_object(dict)
    ctx.obj["path"] = path


@track.group()
@click.pass_context
def sky(ctx: Any) -> None:
    pass


@sky.command()
@click.pass_context
@click.option("--output", help="Output file", type=click.Path(path_type=Path))
def cubemap(ctx: Any, output: Path | None) -> None:
    sky_path = Path(ctx.obj["path"], "SKY.QFS")
    logger.info(f"Sky resource file: {sky_path}")
    data = FshData.from_file(sky_path)
    resources = list(filter(lambda x: fnmatch(x.name, "HDC?"), data.resources))
    image = make_horizon_texture(resources)
    image.save("horizon.png", "png")


@main.group()
def bnk() -> None:
    pass


@bnk.command()
@click.argument("path", type=click.Path(path_type=Path))
def bnk_unpack(path: Path) -> None:
    bnk_data = BnkData.from_file(path)
    audio_streams = bnk_data.sound_streams
    prefix = path.name.replace(".", "_")
    for index, sounds in audio_streams:
        for secidx, sound in enumerate(sounds):
            name = f"{prefix}_{hex(index)}_{secidx}"
            with open(f"{name}.wav", "wb") as f:
                logger.info(f"Unpacking: {name}")
                f.write(raw_stream_to_wav(sound))
