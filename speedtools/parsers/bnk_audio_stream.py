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

ADCPM_SAMPLES_PER_FRAME = 28
ADPCM_FRAME_SIZE = 15


def bnk_find_tlv(tlvs: list[Any], tlv_type: Any) -> list[Any]:
    filtered = filter(lambda tlv: tlv.type is tlv_type, tlvs)
    return list(filtered)


def bnk_find_tlv_value(tlvs: list[Any], tlv_type: Any) -> list[Any]:
    tlvs = bnk_find_tlv(tlvs=tlvs, tlv_type=tlv_type)
    values = (getattr(x.value, "value", None) for x in tlvs)
    return [x for x in values if x is not None]


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
        self.bits_per_sample = bnk_find_tlv_only(
            tlvs=header.tlvs, tlv_type=TlvType.bits_per_sample, default=16
        )
        self.compression = bnk_find_tlv_only(
            tlvs=header.tlvs, tlv_type=TlvType.compression_type, default=0
        )
        self.sample_rate = bnk_find_tlv_only(
            tlvs=header.tlvs, tlv_type=TlvType.sample_rate, default=22050
        )
        self.loop_start = bnk_find_tlv_only(
            tlvs=header.tlvs, tlv_type=TlvType.loop_start, default=-1
        )
        self.loop_end = bnk_find_tlv_only(tlvs=header.tlvs, tlv_type=TlvType.loop_end, default=-1)
        match self.compression:
            case 0x00:  # PCM
                data_size = self.num_samples * self.num_channels * self.bits_per_sample // 8
            case 0x07:  # ADPCM
                frames = -(-self.num_samples // ADCPM_SAMPLES_PER_FRAME)
                data_size = frames * ADPCM_FRAME_SIZE * self.num_channels
            case _:
                logger.debug(f"Unsupported sample compression: {self.compression}")
                data_size = 0

        self.samples = stream.read_bytes(data_size)
