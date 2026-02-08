#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from typing import Any

from more_itertools import one, only

import speedtools.parsers.bnk as bnk

logger = logging.getLogger(__name__)


def bnk_find_tlv(tlvs: list[Any], tlv_type: Any) -> list[Any]:
    filtered = filter(lambda tlv: tlv.type is tlv_type, tlvs)
    return list(filtered)


def bnk_find_tlv_value(tlvs: list[Any], tlv_type: Any) -> list[Any]:
    tlvs = bnk_find_tlv(tlvs=tlvs, tlv_type=tlv_type)
    return [x.value.value for x in tlvs if hasattr(x.value, "value")]


def bnk_find_tlv_only(tlvs: list[Any], tlv_type: Any, default: Any = None):
    return only(bnk_find_tlv_value(tlvs=tlvs, tlv_type=tlv_type), default=default)


def bnk_find_tlv_one(tlvs: list[Any], tlv_type: Any):
    return one(bnk_find_tlv_value(tlvs=tlvs, tlv_type=tlv_type))


class BnkAudioStream:
    def __init__(self, header, stream):
        TlvType = bnk.Bnk.TvType
        self.num_samples = bnk_find_tlv_one(tlvs=header.tlvs, tlv_type=TlvType.num_samples)
        self.num_channels = bnk_find_tlv_only(
            tlvs=header.tlvs, tlv_type=TlvType.channels, default=1
        )
        self.bytes_per_sample = bnk_find_tlv_only(
            tlvs=header.tlvs, tlv_type=TlvType.bytes_per_sample, default=2
        )
        self.compression = bnk_find_tlv_only(
            tlvs=header.tlvs, tlv_type=TlvType.compression_type, default=0
        )
        self.sample_rate = bnk_find_tlv_only(
            tlvs=header.tlvs, tlv_type=TlvType.sample_rate, default=22050
        )
        self.loop_start = bnk_find_tlv_only(
            tlvs=header.tlvs, tlv_type=TlvType.loop_offset, default=0
        )
        self.loop_length = bnk_find_tlv_only(
            tlvs=header.tlvs, tlv_type=TlvType.loop_length, default=0
        )
        match self.compression:
            case 0x00:
                data_size = self.num_samples * self.num_channels * self.bytes_per_sample
            case 0x07:
                MONO_COMPRESSED_SAMPLES_PER_HEADER = 14
                MONO_DECOMPRESSED_TO_COMPRESSED_RATIO = 2
                compressed_samples = self.num_samples // MONO_DECOMPRESSED_TO_COMPRESSED_RATIO
                headers = (
                    compressed_samples + MONO_COMPRESSED_SAMPLES_PER_HEADER - 1
                ) // MONO_COMPRESSED_SAMPLES_PER_HEADER
                data_size = compressed_samples + headers

            case _:
                data_size = 0

        self.samples = stream.read_bytes(data_size)
