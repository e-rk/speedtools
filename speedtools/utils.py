#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
import os
from collections.abc import Callable, Hashable, Iterable, Iterator, Sequence
from contextlib import suppress
from dataclasses import replace
from functools import partial, singledispatch
from io import BytesIO
from itertools import chain, compress, islice
from operator import getitem
from pathlib import Path
from typing import Any, Dict, TypeVar
from base64 import b64encode
from gzip import compress
import struct
import tempfile

from PIL import Image as pil_Image
from click.termui import raw_terminal

from speedtools.types import AudioStream, BaseMesh, BasePolygon, Bitmap, Image, Resource, Vertex

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# sh = logging.StreamHandler()
# sh.setLevel(logging.DEBUG)
# logger.addHandler(sh)

T = TypeVar("T")
Ty = TypeVar("Ty")


def islicen(iterable: Iterable[T], start: int, num: int) -> Iterable[T]:
    return islice(iterable, start, start + num)


def slicen(iterable: Sequence[T], start: int, num: int) -> Sequence[T]:
    return iterable[start : start + num]


def count_repeats_and_map(
    iterable: Iterable[T], func: Callable[[T, int], Ty], key: Callable[[T], Hashable]
) -> Iterable[Ty]:
    count: Dict[Hashable, int] = {}
    for item in iterable:
        k = key(item)
        count[k] = count.setdefault(k, -1) + 1
        yield func(item, count[k])


def unique_named_resources(iterable: Iterable[Resource]) -> Iterable[Resource]:
    def make_unique_name(resource: Resource, repeats: int) -> Resource:
        if repeats == 0:
            return resource
        return Resource(
            name=f"{resource.name}-{repeats}",
            image=resource.image,
            mirrored=resource.mirrored,
            nonmirrored=resource.nonmirrored,
            blend_mode=resource.blend_mode,
        )

    return count_repeats_and_map(iterable=iterable, func=make_unique_name, key=lambda x: x.name)


@singledispatch
def create_pil_image(image: Image) -> Any:
    buffer = BytesIO(image.data)
    return pil_Image.open(fp=buffer)


@create_pil_image.register
def _(image: Bitmap) -> Any:
    return pil_Image.frombytes("RGBA", (image.width, image.height), data=image.data)


def pil_image_to_png(image: Any) -> bytes:
    buffer = BytesIO()
    image.save(buffer, "png")
    return buffer.getvalue()


def image_to_png(image: Image) -> bytes:
    pil_image = create_pil_image(image)
    return pil_image_to_png(pil_image)


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


def remove_unused_vertices(mesh: T) -> T:
    used_vertice_idx = chain.from_iterable(
        polygon.face for polygon in mesh.polygons  # type: ignore[attr-defined]
    )
    used_vertices = list(
        set(map(partial(getitem, mesh.vertices), used_vertice_idx))  # type: ignore[attr-defined]
    )
    mapping = {v: i for i, v in enumerate(used_vertices)}

    def _make_polygon(polygon: BasePolygon) -> BasePolygon:
        vertices = tuple(mesh.vertices[i] for i in polygon.face)  # type: ignore[attr-defined]
        face = tuple(mapping[v] for v in vertices)
        return replace(polygon, face=face)

    polygons = [_make_polygon(polygon) for polygon in mesh.polygons]  # type: ignore[attr-defined]
    return replace(mesh, vertices=used_vertices, polygons=polygons)  # type: ignore[type-var]


def make_subset_mesh(
    mesh: BaseMesh,
    mesh_constructor: Callable[[Iterable[Vertex], Sequence[Ty]], T],
    polygon_constructors: Iterable[Callable[[tuple[int, ...]], Ty]],
    selectors: Iterable[bool],
) -> T:
    selected_polygons = list(compress(mesh.polygons, selectors))
    minimal_mesh = remove_unused_vertices(
        BaseMesh(vertices=mesh.vertices, polygons=selected_polygons)
    )
    constructed_polygons = list(
        map(lambda f, x: f(x.face), polygon_constructors, minimal_mesh.polygons)
    )
    constructed_mesh = mesh_constructor(minimal_mesh.vertices, constructed_polygons)
    return constructed_mesh


def merge_mesh(a: T, b: T) -> T:
    vertices = list(chain(a.vertices, b.vertices))  # type: ignore[attr-defined]

    def remap_idx(polygon: Ty) -> Ty:
        face = tuple(f + len(a.vertices) for f in polygon.face)  # type: ignore[attr-defined]
        return replace(polygon, face=face)  # type: ignore[type-var]

    b_polygons = map(remap_idx, b.polygons)  # type: ignore[attr-defined]
    polygons = list(chain(a.polygons, b_polygons))  # type: ignore[attr-defined]
    return replace(a, vertices=vertices, polygons=polygons)  # type: ignore[type-var]


def make_horizon_texture(resources: list[Resource]) -> Any:
    images = [create_pil_image(x.image) for x in resources]
    width_hrz = sum(x.width for x in images)
    horizon_image = pil_Image.new("RGBA", (width_hrz, width_hrz))
    for idx, image in enumerate(images):
        horizon_image.paste(image, (image.width * idx, width_hrz // 2 - image.width // 2))
    return horizon_image


def raw_stream_to_wav(audio_stream: AudioStream) -> bytes:
    import ffmpeg

    with tempfile.NamedTemporaryFile() as fp:
        stream = (
            ffmpeg.input(
                "pipe:", format="s16le", ar=audio_stream.sample_rate, ac=audio_stream.num_channels
            )
            .output(fp.name, format="wav")
            .overwrite_output()
        )
        logger.debug(stream.get_args())
        process = stream.run_async(pipe_stdin=True)
        process.stdin.write(audio_stream.audio_samples)
        process.stdin.close()
        process.wait()
        data = fp.read()
    loop_end = audio_stream.loop_length
    smpl = struct.pack("<4x4x4x4x4x4x4xl4xllll4x4x", 1, 0, 0, audio_stream.loop_start, loop_end)
    chunk = struct.pack("<4sl", "smpl".encode("ASCII"), len(smpl))
    # smpl = struct.pack("<4s32xl8xlll8x", "smpl".encode("ASCII"), 1, 0, 2, 3)
    return data + chunk + smpl


def raw_stream_to_wav_b64(audio_stream: AudioStream) -> str:
    return b64encode(compress(raw_stream_to_wav(audio_stream))).decode("ascii")
