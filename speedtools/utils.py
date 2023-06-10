#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
import os
from collections.abc import Callable, Hashable, Iterable, Iterator, Sequence
from contextlib import suppress
from functools import partial, singledispatch
from io import BytesIO
from itertools import chain, compress, islice
from operator import getitem
from pathlib import Path
from typing import Any, Dict, Tuple, TypeVar

from PIL import Image as pil_Image

from speedtools.types import (
    BaseMesh,
    BasePolygon,
    Bitmap,
    CollisionMesh,
    DrawableMesh,
    Image,
    Resource,
    Vector3d,
)

logger = logging.getLogger(__name__)

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


def image_to_png(image: Image) -> bytes:
    buffer = BytesIO()
    pil_image = create_pil_image(image)
    pil_image.save(buffer, "png")
    return buffer.getvalue()


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


def remove_unused_vertices(mesh: BaseMesh) -> BaseMesh:
    used_vertice_idx = chain.from_iterable(polygon.face for polygon in mesh.polygons)
    used_vertices = list(set(map(partial(getitem, mesh.vertices), used_vertice_idx)))
    mapping = {v: i for i, v in enumerate(used_vertices)}

    def _make_polygon(polygon: BasePolygon) -> BasePolygon:
        vertices = tuple(mesh.vertices[i] for i in polygon.face)
        face = tuple(mapping[v] for v in vertices)
        return BasePolygon(face=face)

    polygons = [_make_polygon(polygon) for polygon in mesh.polygons]
    return BaseMesh(vertices=used_vertices, polygons=polygons)


def make_subset_mesh(
    mesh: BaseMesh,
    mesh_constructor: Callable[[Iterable[Vector3d], Sequence[Ty]], T],
    polygon_constructors: Iterable[Callable[[Tuple[int, ...]], Ty]],
    selectors: Iterable[bool],
) -> T:
    selected_polygons = list(compress(mesh.polygons, selectors))
    minimal_mesh = remove_unused_vertices(
        BaseMesh(vertices=mesh.vertices, polygons=selected_polygons)
    )
    logger.error(f"Selected: {selected_polygons}")
    # minimal_mesh = BaseMesh(vertices=mesh.vertices, polygons=mesh.polygons)
    logger.error(f"minimal: {minimal_mesh}")
    constructed_polygons = list(
        map(lambda f, x: f(x.face), polygon_constructors, minimal_mesh.polygons)
    )
    logger.error(f"poly: {constructed_polygons}")
    constructed_mesh = mesh_constructor(minimal_mesh.vertices, constructed_polygons)
    return constructed_mesh


def merge_mesh(a: BaseMesh, b: BaseMesh) -> BaseMesh:
    vertices = list(chain(a.vertices, b.vertices))
    b_polygons = map(lambda x: BasePolygon(tuple(f + len(a.vertices) for f in x.face)), b.polygons)
    polygons = list(chain(a.polygons, b_polygons))
    return BaseMesh(vertices=vertices, polygons=polygons)
