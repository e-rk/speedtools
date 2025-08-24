#
# Copyright (c) 2025 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from typing import Any

from more_itertools import first, one, only

import speedtools.parsers.bnk as bnk

logger = logging.getLogger(__name__)


def bnk_find_tlv(tlvs, tlv_type: Any) -> list[Any]:
    TlvType = bnk.Bnk.TvType
    filtered = filter(lambda tlv: tlv.type is tlv_type, tlvs)
    return list(filtered)


def bnk_find_tlv_value(tlvs, tlv_type: Any) -> list[Any]:
    TlvType = bnk.Bnk.TvType
    tlvs = bnk_find_tlv(tlvs=tlvs, tlv_type=tlv_type)
    return [x.value.value for x in tlvs if hasattr(x.value, "value")]


def bnk_find_tlv_only(tlvs, tlv_type: Any, default: Any = None):
    return only(bnk_find_tlv_value(tlvs=tlvs, tlv_type=tlv_type), default=default)


def bnk_find_tlv_one(tlvs, tlv_type: Any):
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
                mul = 15 if self.num_channels == 1 else 30
                mod = 14 if self.num_channels == 1 else 28
                data_size = (
                    (self.num_samples * mul) // 28 + (self.num_samples % mod) + self.num_channels
                )
        self.samples = stream.read_bytes(data_size - 10)
