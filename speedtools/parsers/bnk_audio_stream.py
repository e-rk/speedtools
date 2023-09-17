#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from typing import Any

from more_itertools import only

import speedtools.parsers.bnk as bnk

logger = logging.getLogger(__name__)
# sh = logging.StreamHandler()
# sh.setLevel(logging.DEBUG)
# logger.setLevel(logging.DEBUG)
# logger.addHandler(sh)


def bnk_find_tlv(header, tlv_type: Any, subheader: bool = False) -> Any:
    TlvType = bnk.Bnk.TvType
    tlv = only(filter(lambda tlv: tlv.type is tlv_type, header.tlvs), None)
    logger.debug(f"Tlv = {tlv}, type = {tlv_type}")
    if tlv is None and not subheader:
        subheader = bnk_find_tlv(header=header, tlv_type=TlvType.subheader, subheader=True)
        return bnk_find_tlv(header=subheader, tlv_type=tlv_type, subheader=True)
    return tlv.value if tlv is not None else None


class BnkAudioStream:
    def __init__(self, header, stream):
        TlvType = bnk.Bnk.TvType
        types = (TlvType.num_samples, TlvType.channels, TlvType.bytes_per_sample)
        tlvs = (bnk_find_tlv(header=header, tlv_type=tlv_type) for tlv_type in types)
        num_samples, channels, bytes_per_sample = tlvs
        self.num_samples = num_samples.value
        self.num_channels = channels.value if channels is not None else 1
        self.bytes_per_sample = bytes_per_sample.value if bytes_per_sample is not None else 2
        logger.error(
            f"Samples: {self.num_samples}, Channels: {self.num_channels}, Bytes: {self.bytes_per_sample}"
        )
        data = self.num_samples * self.num_channels * self.bytes_per_sample
        self.samples = stream.read_bytes(data)
