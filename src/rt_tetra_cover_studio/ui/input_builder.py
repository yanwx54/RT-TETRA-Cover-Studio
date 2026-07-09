from __future__ import annotations

from typing import Any

from rt_tetra_cover_studio.io import calculation_input_from_dict
from rt_tetra_cover_studio.models import CalculationInput


SCENARIO_LABELS = {
    "underground": "地下",
    "tunnel": "隧道",
    "ground": "地面",
    "viaduct": "高架",
}

SCENARIO_PARAM_LABELS = {
    "distance_power_loss_coefficient": "距离损耗系数",
    "wall_loss_db": "墙体损耗 dB",
    "floor_loss_db": "楼层损耗 dB",
    "tunnel_width_m": "隧道宽度 m",
    "tunnel_height_m": "隧道高度 m",
    "alpha_db_per_km": "单位距离损耗 dB/km",
    "bend_loss_db": "弯曲损耗 dB",
    "building_height_m": "建筑平均高度 m",
    "building_spacing_m": "建筑间距 m",
    "street_width_m": "街道宽度 m",
    "viaduct_height_m": "高架高度 m",
    "curve_radius_m": "曲线半径 m",
}


def build_input_data(
    *,
    config: dict[str, Any],
    scenario_type: str,
    field_values: dict[str, float],
    scenario_values: dict[str, float],
) -> CalculationInput:
    input_data = {
        **config["wireless"],
        **config["height"],
        "engineering_margin_db": config["engineering_margin_db"],
        "scenario_type": scenario_type,
        "scenario_params": dict(config["scenario_defaults"][scenario_type]),
    }
    input_data.update(field_values)
    input_data["scenario_params"].update(scenario_values)
    return calculation_input_from_dict(input_data)
