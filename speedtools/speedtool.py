#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Sequence
from pathlib import Path

import click

from speedtools.fsh_data import FshData
from speedtools.utils import export_resource, unique_named_resources

logger = logging.getLogger()
logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
logger.addHandler(sh)


@click.command()
@click.option("--output", help="Output directory", type=click.Path(path_type=Path))
@click.argument("files", type=click.Path(path_type=Path), nargs=-1)
def unpack(output: Path | None, files: Sequence[Path]) -> None:
    for file in files:
        logger.info(f"Unpacking: {file}")
        out = Path(file.stem) if output is None else output
        data = FshData.from_file(file)
        resources = unique_named_resources(data.resources)
        export_resource(resources, directory=out)
