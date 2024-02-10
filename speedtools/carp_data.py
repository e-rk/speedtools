#
# Copyright (c) 2024 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import re
from functools import reduce
from typing import Any, Callable, TypeVar

from more_itertools import grouper

T = TypeVar("T")


def listify(constructor: Callable[[str], T]) -> Callable[[str], list[T]]:
    def body(value: str) -> list[T]:
        items = filter(lambda x: x, value.split(","))
        return [constructor(item) for item in items]

    return body


def bool_str(value: str) -> bool:
    return value != "0"


class CarpItem:
    def __init__(self, name: str, constructor: Callable[[str], Any]):
        self.name = name
        self.constructor = constructor

    def to_dict(self, value: str) -> dict[str, Any]:
        return {self.name: self.constructor(value)}


class CarpData:
    CARP_ITEMS = {
        0: CarpItem("serial_number", int),
        1: CarpItem("car_classification", int),
        2: CarpItem("mass", float),
        3: CarpItem("manual_number_of_gears", int),
        75: CarpItem("automatic_number_of_gears", int),
        4: CarpItem("gear_shift_delay", int),
        5: CarpItem("shift_blip_in_rpm", listify(int)),
        6: CarpItem("brake_blip_in_rpm", listify(int)),
        7: CarpItem("manual_velocity_to_rpm_ratio", listify(float)),
        76: CarpItem("automatic_velocity_to_rpm_ratio", listify(float)),
        8: CarpItem("manual_gear_ratios", listify(float)),
        77: CarpItem("automatic_gear_ratios", listify(float)),
        9: CarpItem("manual_gear_efficiency", listify(float)),
        78: CarpItem("automatic_gear_efficiency", listify(float)),
        10: CarpItem("torque_curve", listify(float)),
        11: CarpItem("manual_final_gear", float),
        79: CarpItem("automatic_final_gear", float),
        12: CarpItem("engine_minimum_rpm", int),
        13: CarpItem("engine_redline_rpm", int),
        14: CarpItem("maximum_velocity", float),
        15: CarpItem("top_speed_cap", float),
        16: CarpItem("front_drive_ratio", float),
        17: CarpItem("has_abs", bool_str),
        18: CarpItem("maximum_braking_deceleration", float),
        19: CarpItem("front_bias_brake_ratio", float),
        20: CarpItem("gas_increasing_curve", listify(int)),
        21: CarpItem("gas_decreasing_curve", listify(int)),
        22: CarpItem("brake_increasing_curve", listify(float)),
        23: CarpItem("brake_decreasing_curve", listify(float)),
        24: CarpItem("wheel_base", float),
        25: CarpItem("front_grip_bias", float),
        26: CarpItem("power_steering", bool_str),
        27: CarpItem("minimum_steering_acceleration", float),
        28: CarpItem("turn_in_ramp", float),
        29: CarpItem("turn_out_ramp", float),
        30: CarpItem("lateral_acceleration_grip_multiplier", float),
        80: CarpItem("understeer_gradient", float),
        31: CarpItem("aerodynamic_downforce_multiplier", float),
        32: CarpItem("gas_off_factor", float),
        33: CarpItem("g_transfer_factor", float),
        34: CarpItem("turning_circle_radius", float),
        35: CarpItem("tire_specs_front", listify(int)),
        36: CarpItem("tire_specs_rear", listify(int)),
        37: CarpItem("tire_wear", float),
        38: CarpItem("slide_multiplier", float),
        39: CarpItem("spin_velocity_cap", float),
        40: CarpItem("slide_velocity_cap", float),
        41: CarpItem("slide_assistance_factor", int),
        42: CarpItem("push_factor", int),
        43: CarpItem("low_turn_factor", float),
        44: CarpItem("high_turn_factor", float),
        45: CarpItem("pitch_roll_factor", float),
        46: CarpItem("road_bumpiness_factor", float),
        47: CarpItem("spoiler_function_type", bool_str),
        48: CarpItem("spoiler_activation_speed", float),
        49: CarpItem("gradual_turn_cutoff", int),
        50: CarpItem("medium_turn_cutoff", int),
        51: CarpItem("sharp_turn_cutoff", int),
        52: CarpItem("medium_turn_speed_modifier", float),
        53: CarpItem("sharp_turn_speed_modifier", float),
        54: CarpItem("extreme_turn_speed_modifier", float),
        55: CarpItem("subdivide_level", int),
        56: CarpItem("camera_arm", float),
        57: CarpItem("body_damage", float),
        58: CarpItem("engine_damage", float),
        59: CarpItem("suspension_damage", float),
        60: CarpItem("engine_tuning", float),
        61: CarpItem("brake_balance", float),
        62: CarpItem("steering_speed", float),
        63: CarpItem("gear_rat_factor", float),
        64: CarpItem("suspension_stiffness", float),
        65: CarpItem("aero_factor", float),
        66: CarpItem("tire_factor", float),
        67: CarpItem("ai_acc0", listify(float)),
        68: CarpItem("ai_acc1", listify(float)),
        69: CarpItem("ai_acc2", listify(float)),
        70: CarpItem("ai_acc3", listify(float)),
        71: CarpItem("ai_acc4", listify(float)),
        72: CarpItem("ai_acc5", listify(float)),
        73: CarpItem("ai_acc6", listify(float)),
        74: CarpItem("ai_acc7", listify(float)),
    }

    @classmethod
    def parse(cls, group: tuple[str, str]) -> dict[str, Any]:
        name, value = group
        match = re.findall(r"\((\d+)\)", name)
        key = int(match[-1])
        return cls.CARP_ITEMS[key].to_dict(value)

    @classmethod
    def to_dict(cls, value: str) -> dict[str, Any]:
        values = filter(lambda x: x, value.splitlines())
        grouped = grouper(values, 2, incomplete="strict")
        items = map(cls.parse, grouped)  # type: ignore[arg-type]
        return reduce(lambda x, y: x | y, items)
