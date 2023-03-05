#!/usr/bin/env python3
#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from collections import namedtuple


class Vector3d(namedtuple("Vector3d", ["x", "z", "y"])):
    pass


class Polygon(namedtuple("Polygon", ["face", "uv", "material", "backface_culling"])):
    pass


class Quaternion(namedtuple("Quaternion", ["w", "x", "z", "y"])):
    pass
