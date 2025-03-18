#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from base64 import b16encode
import logging
from collections import namedtuple
from collections.abc import Iterable
from enum import Enum
from typing import Self
from click.types import Path
from more_itertools import one, split_at
from more_itertools.more import filter_map
from speedtools.parsers import BnkParser
from speedtools.parsers.bnk_audio_stream import (
    BnkAudioStream,
    bnk_find_tlv,
    bnk_find_tlv2,
    bnk_find_tlv_one,
    bnk_find_tlv_only,
)
from speedtools.types import AudioStream, BnkTlvType, Compression

logger = logging.getLogger(__name__)
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
logger.addHandler(sh)


def bnk_get_value_or_default(
    entry: BnkParser.SoundEntry, tlv_type: BnkTlvType, default: int
) -> int:
    tlv = bnk_find_tlv(entry.body.header, tlv_type)
    return tlv.value if tlv and hasattr(tlv, "value") else default


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
    def _make_sound_stream(cls, sound_entry: BnkParser.SoundEntry) -> AudioStream:
        separated = split_at(
            sound_entry.body.header.tlvs, lambda x: x.type is BnkTlvType.separator
        )

        ret = []

        for chunk in separated:
            print(chunk)
            subheader = one(bnk_find_tlv2(tlvs=chunk, tlv_type=BnkTlvType.subheader))
            data_tlv = one(
                bnk_find_tlv2(tlvs=subheader.value.tlvs, tlv_type=BnkTlvType.data_start)
            )
            print(data_tlv)

            pitch_unknown0 = bnk_find_tlv_only(
                tlvs=chunk, tlv_type=BnkTlvType.pitch_unknown0, default=60
            )
            pitch_unknown1 = bnk_find_tlv_only(
                tlvs=chunk, tlv_type=BnkTlvType.pitch_unknown1, default=0
            )
            pitch_unknown2 = bnk_find_tlv_only(
                tlvs=chunk, tlv_type=BnkTlvType.pitch_unknown2, default=0
            )

            sound_data = data_tlv.value.body
            match sound_data.compression:
                case 7:
                    compression = Compression.ADPCM
                case _:
                    compression = Compression.PCM
            print(f"***************************{sound_data.compression}****************")
            # print(bytearray(b16encode(sound_data.samples)[0:30]))
            s = AudioStream(
                num_channels=sound_data.num_channels,
                sample_rate=sound_data.sample_rate,
                audio_samples=sound_data.samples,
                loop_start=sound_data.loop_start,
                loop_length=sound_data.loop_length,
                pitch_unknown0=pitch_unknown0,
                pitch_unknown1=pitch_unknown1,
                pitch_unknown2=pitch_unknown2,
                compression=compression,
            )
            ret.append(s)
        return ret[0]

    @property
    def sound_streams(self) -> Iterable[tuple[int, AudioStream]]:
        return filter_map(
            lambda x: (x[0], self._make_sound_stream(x[1])) if x[1].offset > 0 else None,
            enumerate(self.parser.sounds),
        )
