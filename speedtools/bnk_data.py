#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections import namedtuple
from collections.abc import Iterable
from functools import partial
from pathlib import Path
from typing import Any, Self

from more_itertools import one, split_at
from more_itertools.more import filter_map

from speedtools.parsers import BnkParser
from speedtools.parsers.bnk_audio_stream import (
    bnk_find_tlv,
    bnk_find_tlv_only,
)
from speedtools.types import AudioStream, BnkTlvType, Compression

logger = logging.getLogger(__name__)


class AudioChannel(namedtuple("AudioChannel", ["channel", "samples"])):
    pass


class BnkData:
    def __init__(self, parser: BnkParser):
        self.parser = parser

    @classmethod
    def from_file(cls, path: Path) -> Self:
        parser = BnkParser.from_file(path)
        return cls(parser=parser)

    @classmethod
    def _make_sound(cls, tlvs: list[Any]) -> AudioStream | None:
        subheader = one(bnk_find_tlv(tlvs=tlvs, tlv_type=BnkTlvType.subheader))
        data_tlv = one(bnk_find_tlv(tlvs=subheader.value.tlvs, tlv_type=BnkTlvType.data_start))
        sound_data = data_tlv.value.body
        match sound_data.compression:
            case 0:
                compression = Compression.PCM
            case 7:
                compression = Compression.ADPCM
            case _:
                logger.warning(f"Skipping sample with compression {sound_data.compression}")
                return None

        find = partial(bnk_find_tlv_only, tlvs)
        return AudioStream(
            num_channels=sound_data.num_channels,
            sample_rate=sound_data.sample_rate,
            audio_samples=sound_data.samples,
            loop_start=max(sound_data.loop_start, 0),
            loop_end=sound_data.loop_end if sound_data.loop_end > 0 else None,
            decompressed_samples=sound_data.num_samples,
            root_key=find(BnkTlvType.root_key, default=60),
            pitch_bend_range=find(BnkTlvType.pitch_bend_range, default=0),
            detune=find(BnkTlvType.detune, default=0),
            compression=compression,
            volume=find(BnkTlvType.volume, default=127),
            pan=find(BnkTlvType.pan, default=64),
            volume_random_range=find(BnkTlvType.volume_random_range, default=0),
            pan_random_range=find(BnkTlvType.pan_random_range, default=0),
            detune_random_range=find(BnkTlvType.detune_random_range, default=0),
        )

    @classmethod
    def _make_sound_stream(cls, sound_entry: BnkParser.SoundEntry) -> list[AudioStream]:
        separated = split_at(
            sound_entry.body.header.tlvs, lambda x: x.type is BnkTlvType.separator
        )
        return list(filter_map(cls._make_sound, separated))

    @property
    def sound_streams(self) -> Iterable[tuple[int, list[AudioStream]]]:
        return filter_map(
            lambda x: (x[0], self._make_sound_stream(x[1])) if x[1].offset > 0 else None,
            enumerate(self.parser.sounds),
        )
