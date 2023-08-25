#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
import os
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path

import click

from speedtools.fsh_data import FshData
from speedtools.track_data import TrackData
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


@click.command()
@click.option("--output", help="Output directory", type=click.Path())
@click.argument("path", type=click.Path())
def mesh(output: Path, path: Path) -> None:
    with suppress(FileExistsError):
        os.makedirs(output)
    data = TrackData(directory=path, game_root=path.parent.parent.parent)
    materials = set()
    for index, obj in enumerate(data.objects):
        with open(Path(output, f"object_{index}.obj"), "w", encoding="utf-8") as obj_file:
            obj_file.write(f"mtllib materials_{index}.mtl{os.linesep}")
            for vertex in obj.mesh.vertices:
                loc = vertex.location
                obj_file.write(f"v {loc.x} {loc.y} {loc.z}{os.linesep}")
            for i, polygon in enumerate(obj.mesh.polygons):
                for uv in polygon.uv:
                    obj_file.write(f"vt {uv[0]} {uv[1]}{os.linesep}")
                obj_file.write(f"usemtl texture_{polygon.material}{os.linesep}")
                obj_file.write("f")
                for j, f in enumerate(polygon.face, start=1):
                    obj_file.write(f" {f+1}/{4*i + j}")
                obj_file.write(f"{os.linesep}")
                materials.add(polygon.material)

        with open(Path(output, f"materials_{index}.mtl"), "w", encoding="utf-8") as mtl:
            for material in materials:
                out_path = "../images/" + str(int(material) + 2).zfill(4) + ".png"
                mtl.write(
                    f"newmtl texture_{material}{os.linesep}"
                    f"Ka 1.000 1.000 1.000{os.linesep}"
                    f"Kd 1.000 1.000 1.000{os.linesep}"
                    f"Ks 0.000 0.000 0.000{os.linesep}"
                    f"d 1.0{os.linesep}"
                    f"map_Ka {out_path}{os.linesep}"
                    f"map_Kd {out_path}{os.linesep}"
                    f"illum 2{os.linesep}"
                )
