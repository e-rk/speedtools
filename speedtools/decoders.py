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

# int previous_left_sample, previous_right_sample;
# int current_left_sample, current_right_sample;
# int next_left_sample, next_right_sample;
# int coeff1l, coeff2l, coeff1r, coeff2r;
# int shift_left, shift_right;

# /* Each EA ADPCM frame has a 12-byte header followed by 30-byte (stereo) or 15-byte (mono) pieces,
#    each coding 28 stereo/mono samples. */

# if (channels != 2 && channels != 1)
#     return AVERROR_INVALIDDATA;

# current_left_sample   = sign_extend(bytestream2_get_le16u(&gb), 16);
# previous_left_sample  = sign_extend(bytestream2_get_le16u(&gb), 16);
# current_right_sample  = sign_extend(bytestream2_get_le16u(&gb), 16);
# previous_right_sample = sign_extend(bytestream2_get_le16u(&gb), 16);

# for (int count1 = 0; count1 < nb_samples / 28; count1++) {
#     int byte = bytestream2_get_byteu(&gb);
#     coeff1l = ea_adpcm_table[ byte >> 4       ];
#     coeff2l = ea_adpcm_table[(byte >> 4  ) + 4];
#     coeff1r = ea_adpcm_table[ byte & 0x0F];
#     coeff2r = ea_adpcm_table[(byte & 0x0F) + 4];

#     if (channels == 2){
#         byte = bytestream2_get_byteu(&gb);
#         shift_left = 20 - (byte >> 4);
#         shift_right = 20 - (byte & 0x0F);
#     } else{
#         /* Mono packs the shift into the coefficient byte's lower nibble instead */
#         shift_left = 20 - (byte & 0x0F);
#     }

#     for (int count2 = 0; count2 < (channels == 2 ? 28 : 14); count2++) {
#         byte = bytestream2_get_byteu(&gb);
#         next_left_sample  = sign_extend(byte >> 4, 4) * (1 << shift_left);

#         next_left_sample = (next_left_sample +
#             (current_left_sample * coeff1l) +
#             (previous_left_sample * coeff2l) + 0x80) >> 8;

#         previous_left_sample = current_left_sample;
#         current_left_sample = clip_int16(next_left_sample);
#         *samples++ = current_left_sample;

#         if (channels == 2){
#             next_right_sample = sign_extend(byte, 4) * (1 << shift_right);

#             next_right_sample = (next_right_sample +
#                 (current_right_sample * coeff1r) +
#                 (previous_right_sample * coeff2r) + 0x80) >> 8;

#             previous_right_sample = current_right_sample;
#             current_right_sample = clip_int16(next_right_sample);
#             *samples++ = current_right_sample;
#         } else {
#             next_left_sample  = sign_extend(byte, 4) * (1 << shift_left);

#             next_left_sample = (next_left_sample +
#                 (current_left_sample * coeff1l) +
#                 (previous_left_sample * coeff2l) + 0x80) >> 8;

#             previous_left_sample = current_left_sample;
#             current_left_sample = clip_int16(next_left_sample);

#             *samples++ = current_left_sample;
#         }
#     }
# }


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
    print(f"1 {length}")
    # length = length - 129
    # print(f"2 {length}")

    for _ in range(length):  # (int count1 = 0; count1 < nb_samples / 28; count1++) {
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
