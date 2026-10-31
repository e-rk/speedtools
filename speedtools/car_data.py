#
# Copyright (c) 2026 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from functools import partial
from itertools import starmap
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence

from more_itertools import (
    filter_map,
    first,
    groupby_transform,
    one,
    only,
)

from speedtools.bnk_data import BnkData
from speedtools.carp_data import CarpData
from speedtools.fce_data import FceData
from speedtools.fedata_data import FedataData
from speedtools.fsh_data import FshData
from speedtools.parsers import CtbParser, FceParser
from speedtools.types import (
    AudioStream,
    Camera,
    Car,
    CarClass,
    ColorHSV,
    ColorPreset,
    EngineAudio,
    EngineAudioType,
    EngineLocation,
    Image,
    Part,
    Polygon,
    Resource,
    SoundTable,
    Vector3d,
    VehicleLight,
)
from speedtools.utils import get_path_case_insensitive
from speedtools.viv_data import Entry, FedataType, VivData

logger = logging.getLogger(__name__)


class CarData:
    fedata_files: dict[Path, FedataType] = {
        Path("fedata.eng"): Entry.FedataEng,
        Path("fedata.ger"): Entry.FedataGer,
        Path("fedata.fre"): Entry.FedataFre,
        Path("fedata.spa"): Entry.FedataSpa,
        Path("fedata.ita"): Entry.FedataIta,
        Path("fedata.swe"): Entry.FedataSwe,
        Path("fedata.jap"): Entry.FedataJap,
    }
    sfx_resource_file = Path("Data", "GameArt", "SFX.FSH")
    shattered_glass_texture = "shat"

    body_textures = "car00.tga"
    interior_textures = "dash00.tga"

    def __init__(self, directory: Path, game_root: Path) -> None:
        logger.debug(f"Opening directory {directory}")
        self.directory: Path = directory
        self.game_path: Path = game_root
        self.viv: VivData = VivData.from_file(
            get_path_case_insensitive(directory, Path(directory, "CAR.VIV"))
        )
        self.fce: FceData = FceData(self.viv.get(Entry.CarBody))
        self.fedata: FedataData | None = self._open_fedata()

    def _open_fedata(self) -> FedataData | None:
        def _file(filename: Path) -> FedataData | None:
            try:
                path = get_path_case_insensitive(self.directory, Path(self.directory, filename))
                return FedataData.from_file(path)
            except FileNotFoundError:
                return None

        def _viv(entry: FedataType) -> FedataData | None:
            try:
                file = self.viv.get(entry)
                return FedataData(file)
            except FileNotFoundError:
                return None

        def _open(
            fedata: tuple[Path, FedataType],
        ) -> FedataData | None:
            filename, entry = fedata
            file = _file(filename)
            if file:
                return file
            file = _viv(entry)
            return file

        return first(filter_map(_open, self.fedata_files.items()), default=None)

    @property
    def shattered_glass(self) -> Resource:
        sfx_path = get_path_case_insensitive(
            self.game_path, Path(self.game_path, self.sfx_resource_file)
        )
        resources = FshData.from_file(sfx_path).resources
        return one(filter(lambda x: x.name == self.shattered_glass_texture, resources))

    @classmethod
    def _make_hsv(cls, color: FceParser.Color) -> ColorHSV:
        return ColorHSV(hue=color.hue, value=color.value, saturation=color.saturation)

    @classmethod
    def _make_sound_table(
        cls, table_type: EngineAudioType, table: CtbParser
    ) -> Iterable[tuple[int, SoundTable]]:
        table_data = filter(lambda x: x[0] != -1, zip(table.patchnum, table.volume, table.pitch))
        return starmap(
            lambda patchnum, volume, pitch: (
                patchnum,
                SoundTable(volume=volume.value, pitch=pitch.value, table_type=table_type),
            ),
            table_data,
        )

    @staticmethod
    def merge_tables(
        samples: dict[int, list[AudioStream]],
        load: list[tuple[int, SoundTable]],
        coast: list[tuple[int, SoundTable]],
    ) -> Iterable[EngineAudio]:
        def mkenginesound(patchnum: int, tables: list[SoundTable]) -> EngineAudio:
            is_rear = patchnum >= 0x40
            return EngineAudio(
                streams=samples[patchnum],
                tables=tables,
                is_rear=is_rear,
                patchnum=patchnum,
            )

        tables = load + coast
        tables.sort(key=lambda x: x[0])
        table_by_patchnum = groupby_transform(
            tables, keyfunc=lambda x: x[0], valuefunc=lambda x: x[1], reducefunc=list
        )
        return starmap(mkenginesound, table_by_patchnum)

    @property
    def material_map(self) -> Callable[[Polygon], Resource]:
        interior_resource = only(self.interior_materials)
        exterior_resource = one(self.body_materials)

        def inner(polygon: Polygon) -> Resource:
            if polygon.material == 0:
                return exterior_resource
            if interior_resource:
                return interior_resource
            raise KeyError(f"Material {polygon.material} not found")

        return inner

    @classmethod
    def _finalize_part(cls, material: int, part: Part) -> Part:
        polygons = [replace(p, material=material) for p in part.mesh.polygons]
        mesh = replace(part.mesh, polygons=polygons)
        return replace(part, mesh=mesh)

    @property
    def body(self) -> Iterable[Part]:
        return self.fce.parts

    @property
    def interior(self) -> Iterable[Part]:
        try:
            interior = FceData(self.viv.get(Entry.CarInterior))
            return map(partial(self._finalize_part, 1), interior.parts)
        except FileNotFoundError:
            return []

    @property
    def materials(self) -> Iterable[Resource]:
        def mktga(x: Literal[Entry.CarBodyTexture, Entry.CarInteriorTexture]) -> Resource | None:
            try:
                data = self.viv.get(x)
                return Resource(name=x.filename, image=Image(data=data))
            except FileNotFoundError:
                return None

        entries: Sequence[Literal[Entry.CarBodyTexture, Entry.CarInteriorTexture]] = (
            Entry.CarBodyTexture,
            Entry.CarInteriorTexture,
        )
        return filter_map(mktga, entries)

    @property
    def body_materials(self) -> Iterable[Resource]:
        return filter(lambda x: x.name in self.body_textures, self.materials)

    @property
    def interior_materials(self) -> Iterable[Resource]:
        return filter(lambda x: x.name in self.interior_textures, self.materials)

    @property
    def performance(self) -> dict[str, Any]:
        carp = self.viv.get(Entry.Performance)
        parser = CarpData()
        return parser.to_dict(carp)

    @property
    def dimensions(self) -> Vector3d:
        return self.fce.dimensions

    @property
    def lights(self) -> Iterable[VehicleLight]:
        return self.fce.lights

    @property
    def interior_camera(self) -> Camera | None:
        try:
            interior = FceData(self.viv.get(Entry.CarInterior))
            return interior.interior_camera
        except (FileNotFoundError, TypeError, ValueError):
            return None

    @property
    def colors(self) -> Iterable[ColorPreset]:
        return self.fce.colors

    @property
    def engine_audio(self) -> Iterable[EngineAudio]:
        try:
            ctb = self.viv.get(Entry.CarengCtb)
            ltb = self.viv.get(Entry.CarengLtb)
            bnk = self.viv.get(Entry.CarengBnk)
            data = BnkData(bnk)
            samples = dict(data.sound_streams)
            ctb_engine_sounds = list(self._make_sound_table(EngineAudioType.COAST, ctb))
            ltb_engine_sounds = list(self._make_sound_table(EngineAudioType.LOAD, ltb))
            return self.merge_tables(
                samples=samples, load=ltb_engine_sounds, coast=ctb_engine_sounds
            )
        except FileNotFoundError:
            return []

    @property
    def car(self) -> Car:
        engine_location = self.fedata.engine_location if self.fedata else EngineLocation.FRONT
        car_class = self.fedata.car_class if self.fedata else CarClass.NONE
        police = self.fedata.police if self.fedata else False
        return Car(
            parts=list(self.body),
            interior=list(self.interior),
            colors=list(self.colors),
            lights=list(self.lights),
            performance=self.performance,
            dimensions=self.dimensions,
            engine_audio=list(self.engine_audio),
            interior_camera=self.interior_camera,
            engine_location=engine_location,
            car_class=car_class,
            police=police,
            license_plate=self.fce.license_plate,
        )
