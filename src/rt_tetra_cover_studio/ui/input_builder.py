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
    "distance_power_loss_coefficient": "距离损耗系数 N",
    "wall_loss_db": "墙体损耗 (dB)",
    "floor_loss_db": "楼层损耗 (dB)",
    "tunnel_width_m": "隧道宽度 (m)",
    "tunnel_height_m": "隧道高度 (m)",
    "alpha_db_per_km": "单位距离损耗 (dB/km)",
    "bend_loss_db": "弯曲损耗 (dB)",
    "building_height_m": "建筑平均高度 (m)",
    "building_spacing_m": "建筑间距 (m)",
    "street_width_m": "街道宽度 (m)",
    "viaduct_height_m": "高架高度 (m)",
    "curve_radius_m": "曲线半径 (m)",
    "ground_model": "地面传播模型",
    "propagation_condition": "传播条件",
    "city_type": "城市类型",
    "street_orientation_deg": "街道方向角 (degree)",
    "model_correction_db": "模型修正 (dB)",
    "reference_distance_m": "参考距离 (m)",
    "path_loss_exponent": "路径损耗指数 n",
    "calibration_min_distance_m": "标定最小距离 (m)",
    "calibration_max_distance_m": "标定最大距离 (m)",
    "calibration_status": "校准状态",
    "calibration_source": "参数来源",
    "section_correction_db": "截面修正 (dB)",
    "train_blockage_loss_db": "列车遮挡损耗 (dB)",
    "calibration_offset_db": "校准修正 (dB)",
    "viaduct_correction_db": "高架综合修正 (dB)",
}

SCENARIO_PARAM_CHOICES = {
    "ground_model": [
        ("低频标定模型", "low_band"),
        ("COST231-WI", "cost231_wi"),
    ],
    "propagation_condition": [("NLOS", "nlos"), ("LOS", "los")],
    "city_type": [("中小城市/郊区", "medium"), ("大城市中心", "metropolitan")],
    "calibration_status": [("未校准", "unverified"), ("已校准", "calibrated")],
}

LOW_BAND_ONLY_PARAMS = {
    "reference_distance_m",
    "path_loss_exponent",
    "calibration_min_distance_m",
    "calibration_max_distance_m",
}

COST231_ONLY_PARAMS = {
    "propagation_condition",
    "city_type",
    "building_height_m",
    "building_spacing_m",
    "street_width_m",
    "street_orientation_deg",
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
    scenario_values: dict[str, Any],
) -> CalculationInput:
    input_data = {
        **config["wireless"],
        **config["height"],
        **config["coverage_design"],
        "scenario_type": scenario_type,
        "scenario_params": dict(config["scenario_defaults"][scenario_type]),
    }
    input_data.update(field_values)
    input_data["scenario_params"].update(scenario_values)
    if scenario_type in {"ground", "viaduct"}:
        selected_model = input_data["scenario_params"]["ground_model"]
        unused_params = (
            COST231_ONLY_PARAMS
            if selected_model == "low_band"
            else LOW_BAND_ONLY_PARAMS
        )
        for key in unused_params:
            input_data["scenario_params"].pop(key, None)
    return calculation_input_from_dict(input_data)


def split_input_for_fields(
    input_data: CalculationInput,
) -> tuple[dict[str, float], dict[str, float | str]]:
    base_values = {
        "frequency_mhz": input_data.frequency_mhz,
        "base_tx_power_w": input_data.base_tx_power_w,
        "mobile_tx_power_w": input_data.mobile_tx_power_w,
        "base_antenna_gain_dbi": input_data.base_antenna_gain_dbi,
        "base_feeder_loss_db": input_data.base_feeder_loss_db,
        "base_other_loss_db": input_data.base_other_loss_db,
        "mobile_antenna_gain_dbi": input_data.mobile_antenna_gain_dbi,
        "body_loss_db": input_data.body_loss_db,
        "mobile_receiver_sensitivity_dbm": input_data.mobile_receiver_sensitivity_dbm,
        "base_receiver_sensitivity_dbm": input_data.base_receiver_sensitivity_dbm,
        "base_diversity_gain_db": input_data.base_diversity_gain_db,
        "shadow_fading_std_db": input_data.shadow_fading_std_db,
        "edge_coverage_probability_pct": input_data.edge_coverage_probability_pct,
        "interference_margin_db": input_data.interference_margin_db,
        "penetration_loss_db": input_data.penetration_loss_db,
        "base_height_m": input_data.base_height_m,
        "mobile_height_m": input_data.mobile_height_m,
    }
    return base_values, dict(input_data.scenario_params)


def load_example_input(examples_dir: str | Path, scenario_type: str) -> CalculationInput:
    _, filename = EXAMPLE_CASES[scenario_type]
    return load_example_case(Path(examples_dir) / filename)["calculation_input"]
