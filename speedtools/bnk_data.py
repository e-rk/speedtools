#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections import namedtuple
from collections.abc import Iterable
from enum import Enum
from more_itertools.more import filter_map
from speedtools.parsers import BnkParser
from speedtools.parsers.bnk_audio_stream import BnkAudioStream, bnk_find_tlv
from speedtools.types import AudioStream, BnkTlvType

logger = logging.getLogger(__name__)
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
logger.addHandler(sh)


class AudioChannel(namedtuple("AudioChannel", ["channel", "samples"])):
    pass


class BnkData:
    def __init__(self, parser: BnkParser):
        self.parser = parser

    @classmethod
    def _make_sound_stream(cls, sound_entry: BnkParser.SoundEntry) -> AudioStream:
        data_tlv = bnk_find_tlv(header=sound_entry.body.header, tlv_type=BnkTlvType.data_start)
        sample_rate = bnk_find_tlv(header=sound_entry.body.header, tlv_type=BnkTlvType.sample_rate)
        sample_rate = sample_rate.value if sample_rate is not None else 22050
        loop_start = bnk_find_tlv(header=sound_entry.body.header, tlv_type=BnkTlvType.loop_offset)
        loop_start = loop_start.value if loop_start else 0
        loop_length = bnk_find_tlv(header=sound_entry.body.header, tlv_type=BnkTlvType.loop_length)
        loop_length = loop_length.value if loop_length else 0
        sound_data = data_tlv.body
        return AudioStream(
            num_channels=sound_data.num_channels,
            sample_rate=sample_rate,
            audio_samples=sound_data.samples,
            loop_start=loop_start,
            loop_length=loop_length,
        )

    @property
    def sound_streams(self) -> Iterable[tuple[int, AudioStream]]:
        return filter_map(
            lambda x: (x[0], self._make_sound_stream(x[1])) if x[1].offset > 0 else None,
            enumerate(self.parser.sounds),
        )
