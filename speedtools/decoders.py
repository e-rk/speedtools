#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

#
# ADPCM code adapted from FFmpeg adpcm.c.
# Copyright (c) 2000-2025 the FFmpeg developers
#
# The FFmpeg implementation has the shortcoming that it expects the stream
# to be split into 4kB packets, each with its own header.
# I haven't been able to figure out if the whole stream can be processed as a single packet.
#


from io import BytesIO
from struct import pack, unpack

adpcm_table = [0, 240, 460, 392, 0, 0, -208, -220, 0, 1, 3, 4, 7, 8, 10, 11, 0, -1, -3, -4]


def clip_int16(a: int) -> int:
    return max(-32768, min(32767, a))


def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)


def adpcm_to_s16le(stream: bytes, num_channels: int) -> bytes:
    current_left_sample = 0
    previous_left_sample = 0
    current_right_sample = 0
    previous_right_sample = 0

    output = bytes()
    reader = BytesIO(stream)

    div = 30 if num_channels == 2 else 15
    length = len(stream) // div

    for _ in range(length):
        (byte,) = unpack("<B", reader.read(1))
        coeff1l = adpcm_table[byte >> 4]
        coeff2l = adpcm_table[(byte >> 4) + 4]
        coeff1r = adpcm_table[byte & 0x0F]
        coeff2r = adpcm_table[(byte & 0x0F) + 4]

        if num_channels == 2:
            (byte,) = unpack("<b", reader.read(1))
            shift_left = 20 - (byte >> 4)
            shift_right = 20 - (byte & 0x0F)
        else:
            shift_left = 20 - (byte & 0x0F)
            shift_right = 0

        iters = 28 if num_channels == 2 else 14
        for _ in range(iters):
            (byte,) = unpack("<b", reader.read(1))
            next_left_sample = sign_extend(byte >> 4, 4) * (1 << shift_left)

            next_left_sample = (
                next_left_sample
                + (current_left_sample * coeff1l)
                + (previous_left_sample * coeff2l)
                + 0x80
            ) >> 8

            previous_left_sample = current_left_sample
            current_left_sample = clip_int16(next_left_sample)
            output += pack("<h", current_left_sample)

            if num_channels == 2:
                next_right_sample = sign_extend(byte, 4) * (1 << shift_right)

                next_right_sample = (
                    next_right_sample
                    + (current_right_sample * coeff1r)
                    + (previous_right_sample * coeff2r)
                    + 0x80
                ) >> 8

                previous_right_sample = current_right_sample
                current_right_sample = clip_int16(next_right_sample)
                output += pack("<h", current_right_sample)
            else:
                next_left_sample = sign_extend(byte, 4) * (1 << shift_left)

                next_left_sample = (
                    next_left_sample
                    + (current_left_sample * coeff1l)
                    + (previous_left_sample * coeff2l)
                    + 0x80
                ) >> 8

                previous_left_sample = current_left_sample
                current_left_sample = clip_int16(next_left_sample)

                output += pack("<h", current_left_sample)

    return bytes(output)
