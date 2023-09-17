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


class BnkData(BnkParser):
    @classmethod
    def _make_sound_stream(cls, sound_entry: BnkParser.SoundEntry) -> AudioStream:
        data_tlv = bnk_find_tlv(header=sound_entry.body.header, tlv_type=BnkTlvType.data_start)
        sample_rate = bnk_find_tlv(header=sound_entry.body.header, tlv_type=BnkTlvType.sample_rate)
        sample_rate = sample_rate.value if sample_rate is not None else 22050
        sound_data = data_tlv.body
        return AudioStream(
            num_channels=sound_data.num_channels,
            sample_rate=sample_rate,
            audio_samples=sound_data.samples,
        )

    @property
    def sound_streams(self) -> Iterable[AudioStream]:
        valid_data = filter(lambda x: x.offset > 0, self.sounds)
        return map(self._make_sound_stream, valid_data)


if __name__ == "__main__":
    data = BnkData.from_file("D:/Gry/nfshs/Need For Speed High Stakes/Data/AUDIO/SFX/SIREN.BNK")

    for index, sound in enumerate(data.sound_streams):
        stream = ffmpeg.input(
            "pipe:", format="s16le", ar=sound.sample_rate, ac=sound.num_channels
        ).output(f"out_{index}.wav")
        logger.debug(stream.get_args())
        process = stream.overwrite_output().run_async(pipe_stdin=True)
        process.stdin.write(sound.audio_samples)
        process.stdin.close()
        process.wait()
