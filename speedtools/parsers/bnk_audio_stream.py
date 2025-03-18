#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from typing import Any

from more_itertools import first, only, one

import speedtools.parsers.bnk as bnk

logger = logging.getLogger(__name__)
# sh = logging.StreamHandler()
# sh.setLevel(logging.DEBUG)
# logger.setLevel(logging.DEBUG)
# logger.addHandler(sh)


def bnk_find_tlv2(tlvs, tlv_type: Any) -> list[Any]:
    TlvType = bnk.Bnk.TvType
    filtered = filter(lambda tlv: tlv.type is tlv_type, tlvs)
    return list(filtered)


def bnk_find_tlv_value(tlvs, tlv_type: Any) -> list[Any]:
    TlvType = bnk.Bnk.TvType
    tlvs = bnk_find_tlv2(tlvs=tlvs, tlv_type=tlv_type)
    return [x.value.value for x in tlvs if hasattr(x.value, "value")]


def bnk_find_tlv_only(tlvs, tlv_type: Any, default: Any = None):
    return only(bnk_find_tlv_value(tlvs=tlvs, tlv_type=tlv_type), default=default)


def bnk_find_tlv_one(tlvs, tlv_type: Any):
    return one(bnk_find_tlv_value(tlvs=tlvs, tlv_type=tlv_type))


def bnk_find_tlv(header, tlv_type: Any, default: Any = None, subheader: bool = False) -> Any:
    TlvType = bnk.Bnk.TvType
    tlv = only(filter(lambda tlv: tlv.type is tlv_type, header.tlvs), None)
    logger.debug(f"Tlv = {tlv}, type = {tlv_type}")
    if tlv is None and not subheader:
        subheader = bnk_find_tlv(
            header=header, tlv_type=TlvType.subheader, default=None, subheader=True
        )
        return bnk_find_tlv(header=subheader, tlv_type=tlv_type, default=default, subheader=True)
    return tlv.value if tlv is not None else default


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
        logger.error(
            f"Samples: {self.num_samples}, Channels: {self.num_channels}, Bytes: {self.bytes_per_sample}, Compression: {self.compression}"
        )
        data = self.num_samples * self.num_channels * self.bytes_per_sample
        data = data // 4 if self.compression == 0x07 else data
        # logger.error(f"**************{data}")
        self.samples = stream.read_bytes(data)
