#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from struct import unpack

logger = logging.getLogger(__name__)


@dataclass
class Opcode:
    proclen: int
    reflen: int
    refdist: int

    @property
    def is_stop(self) -> bool:
        return self.proclen < 4 and self.reflen == 0 and self.refdist == 0


class Refpack:
    def __init__(self, expanded_length: int):
        self.expanded_length = expanded_length
        logger.debug(self.expanded_length)

    def decode(self, compressed_data: bytes) -> bytes:
        decompressed_data = bytearray()

        for cmd, data in self._decode_cmd(compressed_data):
            logger.debug(f"Decompressing: {cmd}")
            decompressed_data.extend(data)

            for _ in range(cmd.reflen):
                decompressed_data.append(decompressed_data[-cmd.refdist])

        if len(decompressed_data) != self.expanded_length:
            raise ValueError(
                f"Bad decompressed length {len(decompressed_data)} != {self.expanded_length}"
            )

        return bytes(decompressed_data)

    def _decode_cmd(self, compressed_data: bytes) -> Iterator[tuple[Opcode, bytearray]]:
        current = bytearray(compressed_data)
        while True:
            (opcode,) = unpack("<B", current[:1])
            logger.debug(f"opcode: {opcode}")
            if opcode & 0x80 == 0:
                cmd = self._decode_2b_cmd(current[:2])
                del current[:2]
            elif opcode & 0xC0 == 0x80:
                cmd = self._decode_3b_cmd(current[:3])
                del current[:3]
            elif opcode & 0xE0 == 0xC0:
                cmd = self._decode_4b_cmd(current[:4])
                del current[:4]
            elif opcode & 0xE0 == 0xE0:
                cmd = self._decode_1b_cmd(current[:1])
                del current[:1]
            else:
                raise ValueError("Bad opcode")

            logger.debug(cmd)
            logger.debug(f"Remaining: {len(current)}")

            yield cmd, current[: cmd.proclen]
            del current[: cmd.proclen]

            if cmd.is_stop:
                break

    def _decode_2b_cmd(self, opdata: bytearray) -> Opcode:
        a, b = unpack("BB", opdata)
        proclen = a & 0x03
        reflen = ((a & 0x1C) >> 2) + 3
        refdist = ((a & 0x60) << 3) + b + 1
        return Opcode(proclen=proclen, refdist=refdist, reflen=reflen)

    def _decode_3b_cmd(self, opdata: bytearray) -> Opcode:
        a, b, c = unpack("BBB", opdata)
        proclen = (b & 0xC0) >> 6
        reflen = (a & 0x3F) + 4
        refdist = ((b & 0x3F) << 8) + c + 1
        return Opcode(proclen=proclen, refdist=refdist, reflen=reflen)

    def _decode_4b_cmd(self, opdata: bytearray) -> Opcode:
        a, b, c, d = unpack("BBBB", opdata)
        proclen = a & 0x03
        reflen = ((a & 0x0C) << 6) + d + 5
        refdist = ((a & 0x10) << 12) + (b << 8) + c + 1
        return Opcode(proclen=proclen, refdist=refdist, reflen=reflen)

    def _decode_1b_cmd(self, opdata: bytearray) -> Opcode:
        (a,) = unpack("B", opdata)
        if a < 0xFC:
            proclen = ((a & 0x1F) + 1) << 2
        else:
            proclen = a & 0x03
        return Opcode(proclen=proclen, refdist=0, reflen=0)
