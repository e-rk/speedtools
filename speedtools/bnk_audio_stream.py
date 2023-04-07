#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging

from speedtools.utils import bnk_find_tlv

logger = logging.getLogger(__name__)
# sh = logging.StreamHandler()
# sh.setLevel(logging.DEBUG)
# logger.setLevel(logging.DEBUG)
# logger.addHandler(sh)


class BnkAudioStream:
    def __init__(self, header, stream):
        logger.debug(f"{vars(header)}")
        TlvType = header._root.TvType
        types = (TlvType.num_samples, TlvType.channels, TlvType.bytes_per_sample)
        tlvs = (bnk_find_tlv(header=header, tlv_type=tlv_type) for tlv_type in types)
        num_samples, channels, bytes_per_sample = tlvs
        self.num_samples = num_samples.value
        self.num_channels = channels.value if channels is not None else 1
        self.bytes_per_sample = bytes_per_sample.value if bytes_per_sample is not None else 2
        logger.debug(
            f"Samples: {self.num_samples}, Channels: {self.num_channels}, Bytes: {self.bytes_per_sample}"
        )
        bytes = self.num_samples * self.num_channels * self.bytes_per_sample
        self.samples = stream.read_bytes(bytes)
