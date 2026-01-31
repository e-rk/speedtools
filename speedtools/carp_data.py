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


def float_to_int(value: str) -> int:
    return int(float(value))


def remove_consecutive_dots(value: str) -> str:
    result = ""
    dot_found = False
    for x in value:
        if dot_found and x == ".":
            continue
        elif x == ".":
            dot_found = True
        else:
            dot_found = False
        result += x
    return result


def float_relaxed(value: str) -> float:
    sanitized = remove_consecutive_dots(value)
    # TODO: Figure out if the fractional part occuring after multiple dots
    # should be ignored or not.
    return float(sanitized)


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
        2: CarpItem("mass", float_relaxed),
        3: CarpItem("manual_number_of_gears", int),
        75: CarpItem("automatic_number_of_gears", int),
        4: CarpItem("gear_shift_delay", int),
        5: CarpItem("shift_blip_in_rpm", listify(int)),
        6: CarpItem("brake_blip_in_rpm", listify(int)),
        7: CarpItem("manual_velocity_to_rpm_ratio", listify(float_relaxed)),
        76: CarpItem("automatic_velocity_to_rpm_ratio", listify(float_relaxed)),
        8: CarpItem("manual_gear_ratios", listify(float_relaxed)),
        77: CarpItem("automatic_gear_ratios", listify(float_relaxed)),
        9: CarpItem("manual_gear_efficiency", listify(float_relaxed)),
        78: CarpItem("automatic_gear_efficiency", listify(float_relaxed)),
        10: CarpItem("torque_curve", listify(float_relaxed)),
        11: CarpItem("manual_final_gear", float_relaxed),
        79: CarpItem("automatic_final_gear", float_relaxed),
        12: CarpItem("engine_minimum_rpm", int),
        13: CarpItem("engine_redline_rpm", int),
        14: CarpItem("maximum_velocity", float_relaxed),
        15: CarpItem("top_speed_cap", float_relaxed),
        16: CarpItem("front_drive_ratio", float_relaxed),
        17: CarpItem("has_abs", bool_str),
        18: CarpItem("maximum_braking_deceleration", float_relaxed),
        19: CarpItem("front_bias_brake_ratio", float_relaxed),
        20: CarpItem("gas_increasing_curve", listify(int)),
        21: CarpItem("gas_decreasing_curve", listify(int)),
        22: CarpItem("brake_increasing_curve", listify(float_relaxed)),
        23: CarpItem("brake_decreasing_curve", listify(float_relaxed)),
        24: CarpItem("wheel_base", float_relaxed),
        25: CarpItem("front_grip_bias", float_relaxed),
        26: CarpItem("power_steering", bool_str),
        27: CarpItem("minimum_steering_acceleration", float_relaxed),
        28: CarpItem("turn_in_ramp", float_relaxed),
        29: CarpItem("turn_out_ramp", float_relaxed),
        30: CarpItem("lateral_acceleration_grip_multiplier", float_relaxed),
        80: CarpItem("understeer_gradient", float_relaxed),
        31: CarpItem("aerodynamic_downforce_multiplier", float_relaxed),
        32: CarpItem("gas_off_factor", float_relaxed),
        33: CarpItem("g_transfer_factor", float_relaxed),
        34: CarpItem("turning_circle_radius", float_relaxed),
        35: CarpItem("tire_specs_front", listify(int)),
        36: CarpItem("tire_specs_rear", listify(int)),
        37: CarpItem("tire_wear", float_relaxed),
        38: CarpItem("slide_multiplier", float_relaxed),
        39: CarpItem("spin_velocity_cap", float_relaxed),
        40: CarpItem("slide_velocity_cap", float_relaxed),
        41: CarpItem("slide_assistance_factor", float_to_int),
        42: CarpItem("push_factor", int),
        43: CarpItem("low_turn_factor", float_relaxed),
        44: CarpItem("high_turn_factor", float_relaxed),
        45: CarpItem("pitch_roll_factor", float_relaxed),
        46: CarpItem("road_bumpiness_factor", float_relaxed),
        47: CarpItem("spoiler_function_type", bool_str),
        48: CarpItem("spoiler_activation_speed", float_relaxed),
        49: CarpItem("gradual_turn_cutoff", int),
        50: CarpItem("medium_turn_cutoff", int),
        51: CarpItem("sharp_turn_cutoff", int),
        52: CarpItem("medium_turn_speed_modifier", float_relaxed),
        53: CarpItem("sharp_turn_speed_modifier", float_relaxed),
        54: CarpItem("extreme_turn_speed_modifier", float_relaxed),
        55: CarpItem("subdivide_level", int),
        56: CarpItem("camera_arm", float_relaxed),
        57: CarpItem("body_damage", float_relaxed),
        58: CarpItem("engine_damage", float_relaxed),
        59: CarpItem("suspension_damage", float_relaxed),
        60: CarpItem("engine_tuning", float_relaxed),
        61: CarpItem("brake_balance", float_relaxed),
        62: CarpItem("steering_speed", float_relaxed),
        63: CarpItem("gear_rat_factor", float_relaxed),
        64: CarpItem("suspension_stiffness", float_relaxed),
        65: CarpItem("aero_factor", float_relaxed),
        66: CarpItem("tire_factor", float_relaxed),
        67: CarpItem("ai_acc0", listify(float_relaxed)),
        68: CarpItem("ai_acc1", listify(float_relaxed)),
        69: CarpItem("ai_acc2", listify(float_relaxed)),
        70: CarpItem("ai_acc3", listify(float_relaxed)),
        71: CarpItem("ai_acc4", listify(float_relaxed)),
        72: CarpItem("ai_acc5", listify(float_relaxed)),
        73: CarpItem("ai_acc6", listify(float_relaxed)),
        74: CarpItem("ai_acc7", listify(float_relaxed)),
    }

    @classmethod
    def parse(cls, group: tuple[str, str]) -> dict[str, Any]:
        name, value = group
        match = re.findall(r"\((\d+)\)", name)
        key = int(match[-1])
        return cls.CARP_ITEMS[key].to_dict(value)

    @classmethod
    def to_dict(cls, value: str) -> dict[str, Any]:
        values = filter(lambda x: x and not x.isspace(), value.splitlines())
        grouped = grouper(values, 2, incomplete="strict")
        items = map(cls.parse, grouped)  # type: ignore[arg-type]
        return reduce(lambda x, y: x | y, items)
