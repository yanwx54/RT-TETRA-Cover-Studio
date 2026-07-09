from __future__ import annotations

from pathlib import Path
from typing import Any

from rt_tetra_cover_studio.io import calculation_input_from_dict, load_example_case
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

EXAMPLE_CASES = {
    "underground": ("地下站厅标准算例", "underground_standard.json"),
    "tunnel": ("隧道区间标准算例", "tunnel_standard.json"),
    "ground": ("地面区段标准算例", "ground_standard.json"),
    "viaduct": ("高架区段标准算例", "viaduct_standard.json"),
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


def split_input_for_fields(input_data: CalculationInput) -> tuple[dict[str, float], dict[str, float]]:
    base_values = {
        "frequency_mhz": input_data.frequency_mhz,
        "tx_power_dbm": input_data.tx_power_dbm,
        "base_antenna_gain_dbi": input_data.base_antenna_gain_dbi,
        "feeder_loss_db": input_data.feeder_loss_db,
        "connector_loss_db": input_data.connector_loss_db,
        "mobile_antenna_gain_dbi": input_data.mobile_antenna_gain_dbi,
        "receiver_sensitivity_dbm": input_data.receiver_sensitivity_dbm,
        "base_height_m": input_data.base_height_m,
        "mobile_height_m": input_data.mobile_height_m,
        "engineering_margin_db": input_data.engineering_margin_db,
    }
    return base_values, dict(input_data.scenario_params)


def load_example_input(examples_dir: str | Path, scenario_type: str) -> CalculationInput:
    _, filename = EXAMPLE_CASES[scenario_type]
    return load_example_case(Path(examples_dir) / filename)["calculation_input"]
