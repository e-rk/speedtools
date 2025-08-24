#
# Copyright (c) 2025 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from functools import reduce
import logging
from collections import namedtuple
from typing import Self
from pathlib import Path
from more_itertools import one, split_at
from more_itertools.more import filter_map
from speedtools.parsers import BnkParser
from speedtools.parsers.bnk_audio_stream import bnk_find_tlv
from speedtools.types import AudioEncoding, AudioStream, BnkTlvType

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
    def _make_chunk(cls, chunk) -> AudioStream:
        subheader = one(bnk_find_tlv(tlvs=chunk, tlv_type=BnkTlvType.subheader))
        data_tlv = one(bnk_find_tlv(tlvs=subheader.value.tlvs, tlv_type=BnkTlvType.data_start))
        sound_data = data_tlv.value.body
        match sound_data.compression:
            case 7:
                encoding = AudioEncoding.ADPCM
            case _:
                encoding = AudioEncoding.PCM_S16LE
        return AudioStream(
            num_channels=sound_data.num_channels,
            sample_rate=sound_data.sample_rate,
            audio_samples=sound_data.samples,
            loop_start=sound_data.loop_start,
            loop_length=sound_data.loop_length,
            encoding=encoding,
        )

    @classmethod
    def _make_sound_stream(cls, sound_entry: BnkParser.SoundEntry) -> list[AudioStream]:
        separated = split_at(
            sound_entry.body.header.tlvs, lambda x: x.type is BnkTlvType.separator
        )
        return [cls._make_chunk(chunk) for chunk in separated]

    @property
    def sound_streams(self) -> dict[int, list[AudioStream]]:
        filtered = filter_map(
            lambda x: {x[0]: self._make_sound_stream(x[1])} if x[1].offset > 0 else None,
            enumerate(self.parser.sounds),
        )
        return reduce(lambda a, b: a | b, filtered)
