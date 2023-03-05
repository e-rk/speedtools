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

import click
from PIL import Image

from speedtools.track_data import TrackData

logger = logging.getLogger(__name__)


@click.command()
@click.option("--output", help="Output directory", type=click.Path())
@click.argument("path", type=click.Path())
def unpack(output, path):
    with suppress(FileExistsError):
        os.makedirs(output)
    data = TrackData(path)
    for bitmap in data.track_bitmaps:
        logger.info(f"Unpacking image: {bitmap.id}")
        image = Image.frombytes("RGBA", (bitmap.width, bitmap.height), data=bitmap.rgba)
        image.save(Path(output, f"{bitmap.id}.png"))


@click.command()
@click.option("--output", help="Output directory", type=click.Path())
@click.argument("path", type=click.Path())
def obj(output, path):
    with suppress(FileExistsError):
        os.makedirs(output)
    data = TrackData(path)
    materials = set()
    for index, object in enumerate(data.objects):
        with open(Path(output, f"object_{index}.obj"), "w") as obj_file:
            obj_file.write(f"mtllib materials_{index}.mtl{os.linesep}")
            for vertex in object.vertices:
                obj_file.write(f"v {vertex.x} {vertex.y} {vertex.z}{os.linesep}")
            for i, polygon in enumerate(object.polygons):
                for uv in polygon.uv:
                    obj_file.write(f"vt {uv[0]} {uv[1]}{os.linesep}")
                obj_file.write(f"usemtl texture_{polygon.material}{os.linesep}")
                obj_file.write("f")
                for j, f in enumerate(polygon.face, start=1):
                    obj_file.write(f" {f+1}/{4*i + j}")
                obj_file.write(f"{os.linesep}")
                materials.add(polygon.material)

        with open(Path(output, f"materials_{index}.mtl"), "w") as mtl:
            for material in materials:
                path = "../images/" + str(int(material) + 2).zfill(4) + ".png"
                mtl.write(
                    f"newmtl texture_{material}{os.linesep}"
                    f"Ka 1.000 1.000 1.000{os.linesep}"
                    f"Kd 1.000 1.000 1.000{os.linesep}"
                    f"Ks 0.000 0.000 0.000{os.linesep}"
                    f"d 1.0{os.linesep}"
                    f"map_Ka {path}{os.linesep}"
                    f"map_Kd {path}{os.linesep}"
                    f"illum 2{os.linesep}"
                )
