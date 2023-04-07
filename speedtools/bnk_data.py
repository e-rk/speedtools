#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections import namedtuple
from enum import Enum

import ffmpeg

from speedtools.parsers import BnkParser
from speedtools.types import BnkTlvType
from speedtools.utils import bnk_find_tlv

logger = logging.getLogger(__name__)
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
logger.addHandler(sh)


class Channel(Enum):
    Left = 1
    Right = 2
    Mono = 3


class AudioChannel(namedtuple("AudioChannel", ["channel", "samples"])):
    pass


class AudioStream(namedtuple("AudioStream", ["sample_rate", "channels"])):
    pass


class BnkData(BnkParser):
    @property
    def sound_streams(self):
        for sound in filter(lambda x: x.body is not None, self.sounds):
            data_tlv = bnk_find_tlv(header=sound.body.header, tlv_type=BnkTlvType.data_start)
            sample_rate = bnk_find_tlv(header=sound.body.header, tlv_type=BnkTlvType.sample_rate)
            sample_rate = sample_rate.value if sample_rate is not None else 22050
            sound_data = data_tlv.body
            channels = []
            if sound_data.num_channels == 1:
                channels.append(AudioChannel(channel=Channel.Mono, samples=sound_data.samples))
            yield AudioStream(sample_rate=sample_rate, channels=channels)


if __name__ == "__main__":
    data = BnkData.from_file("D:/Gry/nfshs/Need For Speed High Stakes/Data/AUDIO/SFX/CRATE.BNK")

    for index, sound in enumerate(data.sound_streams):
        logger.debug(f"{len(sound.channels)}")
        stream = ffmpeg.input(
            "pipe:", format="u16le", ar=sound.sample_rate, ac=len(sound.channels)
        ).output(f"out_{index}.wav")
        logger.debug(stream.get_args())
        process = stream.overwrite_output().run_async(pipe_stdin=True)
        process.stdin.write(sound.channels[0].samples)
        process.stdin.close()
        process.wait()
