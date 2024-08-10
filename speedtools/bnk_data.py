#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections import namedtuple
from collections.abc import Iterable
from enum import Enum

import ffmpeg

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
        print(loop_start)
        sound_data = data_tlv.body
        return AudioStream(
            num_channels=sound_data.num_channels,
            sample_rate=sample_rate,
            audio_samples=sound_data.samples,
            loop_start=loop_start,
            loop_length=loop_length,
        )

    @property
    def sound_streams(self) -> Iterable[AudioStream]:
        valid_data = filter(lambda x: x.offset > 0, self.parser.sounds)
        return map(self._make_sound_stream, valid_data)
