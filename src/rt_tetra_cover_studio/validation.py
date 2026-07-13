from __future__ import annotations

from .models import CalculationInput


SUPPORTED_SCENARIOS = {"underground", "tunnel", "ground", "viaduct"}

REQUIRED_SCENARIO_PARAMS = {
    "underground": set(),
    "tunnel": {
        "tunnel_width_m",
        "tunnel_height_m",
        "alpha_db_per_km",
        "section_correction_db",
        "calibration_status",
        "calibration_source",
    },
    "ground": {"ground_model"},
    "viaduct": {
        "ground_model",
        "viaduct_height_m",
        "viaduct_correction_db",
        "calibration_status",
        "calibration_source",
    },
}

COST231_WI_PARAMS = {
    "propagation_condition",
    "city_type",
    "building_height_m",
    "building_spacing_m",
    "street_width_m",
    "street_orientation_deg",
    "model_correction_db",
}

LOW_BAND_PARAMS = {
    "reference_distance_m",
    "path_loss_exponent",
    "model_correction_db",
    "calibration_min_distance_m",
    "calibration_max_distance_m",
    "calibration_status",
    "calibration_source",
}


def validate_input(input_data: CalculationInput) -> list[str]:
    errors: list[str] = []

    if input_data.frequency_mhz <= 0:
        errors.append("工作频率必须大于 0 MHz。")
    if input_data.base_tx_power_w <= 0:
        errors.append("基站发射功率必须大于 0 W。")
    if input_data.mobile_tx_power_w <= 0:
        errors.append("移动台发射功率必须大于 0 W。")
    if input_data.base_feeder_loss_db < 0:
        errors.append("馈线损耗不能小于 0 dB。")
    if input_data.base_other_loss_db < 0:
        errors.append("基站其他损耗不能小于 0 dB。")
    if input_data.body_loss_db < 0:
        errors.append("人体损耗不能小于 0 dB。")
    if input_data.mobile_receiver_sensitivity_dbm >= 0:
        errors.append("移动台接收灵敏度应为负 dBm 值。")
    if input_data.base_receiver_sensitivity_dbm >= 0:
        errors.append("基站接收灵敏度应为负 dBm 值。")
    if input_data.base_diversity_gain_db < 0:
        errors.append("基站分集增益不能小于 0 dB。")
    if input_data.shadow_fading_std_db < 0:
        errors.append("阴影衰落标准差不能小于 0 dB。")
    if not 50.0 <= input_data.edge_coverage_probability_pct < 100.0:
        errors.append("边缘覆盖率必须大于等于 50% 且小于 100%。")
    if input_data.interference_margin_db < 0:
        errors.append("干扰余量不能小于 0 dB。")
    if input_data.penetration_loss_db < 0:
        errors.append("穿透损耗不能小于 0 dB。")
    if input_data.base_height_m <= 0:
        errors.append("基站高度必须大于 0 m。")
    if input_data.mobile_height_m <= 0:
        errors.append("手台高度必须大于 0 m。")
    if input_data.scenario_type not in SUPPORTED_SCENARIOS:
        errors.append("场景类型必须是 underground、tunnel、ground 或 viaduct。")
    else:
        required_params = set(REQUIRED_SCENARIO_PARAMS[input_data.scenario_type])
        if input_data.scenario_type in {"ground", "viaduct"}:
            ground_model = input_data.scenario_params.get("ground_model")
            if ground_model == "cost231_wi":
                required_params.update(COST231_WI_PARAMS)
            elif ground_model == "low_band":
                required_params.update(LOW_BAND_PARAMS)
            else:
                errors.append("地面模型必须是 cost231_wi 或 low_band。")
        missing_params = required_params - set(input_data.scenario_params)
        if missing_params:
            errors.append(f"场景参数缺失：{', '.join(sorted(missing_params))}。")

    _validate_scenario_params(input_data, errors)

    return errors


def _validate_scenario_params(
    input_data: CalculationInput, errors: list[str]
) -> None:
    params = input_data.scenario_params
    nonnegative_params = {
        "wall_loss_db",
        "floor_loss_db",
        "alpha_db_per_km",
        "bend_loss_db",
        "section_correction_db",
        "train_blockage_loss_db",
        "viaduct_height_m",
        "curve_radius_m",
    }
    for name in nonnegative_params:
        value = params.get(name)
        if isinstance(value, int | float) and value < 0:
            errors.append(f"场景参数 {name} 不能小于 0。")
    for name in {
        "tunnel_width_m",
        "tunnel_height_m",
        "building_height_m",
        "building_spacing_m",
        "street_width_m",
    }:
        value = params.get(name)
        if isinstance(value, int | float) and value <= 0:
            errors.append(f"场景参数 {name} 必须大于 0。")

    if input_data.scenario_type == "underground":
        coefficient = params.get("distance_power_loss_coefficient")
        if isinstance(coefficient, int | float) and coefficient <= 0:
            errors.append("地下距离损耗系数必须大于 0。")

    if "calibration_status" in params and params.get("calibration_status") not in {
        "unverified",
        "calibrated",
    }:
        errors.append("校准状态必须是 unverified 或 calibrated。")
    if "calibration_source" in params:
        source = params.get("calibration_source")
        if not isinstance(source, str) or not source.strip():
            errors.append("必须填写模型参数或校准数据来源。")

    if input_data.scenario_type not in {"ground", "viaduct"}:
        return

    ground_model = params.get("ground_model")
    if ground_model == "cost231_wi":
        if not 800.0 <= input_data.frequency_mhz <= 2000.0:
            errors.append("COST231-WI 频率必须在 800 至 2000 MHz 之间。")
        if not 4.0 <= input_data.base_height_m <= 50.0:
            errors.append("COST231-WI 基站高度必须在 4 至 50 m 之间。")
        if not 1.0 <= input_data.mobile_height_m <= 3.0:
            errors.append("COST231-WI 移动台高度必须在 1 至 3 m 之间。")
        orientation = params.get("street_orientation_deg")
        if isinstance(orientation, int | float) and not 0.0 <= orientation <= 90.0:
            errors.append("街道方向角必须在 0 至 90 度之间。")
        if params.get("propagation_condition") not in {"los", "nlos"}:
            errors.append("COST231-WI 传播条件必须是 los 或 nlos。")
        if params.get("city_type") not in {"medium", "metropolitan"}:
            errors.append("COST231-WI 城市类型必须是 medium 或 metropolitan。")
        building_height = params.get("building_height_m")
        if (
            params.get("propagation_condition") == "nlos"
            and isinstance(building_height, int | float)
            and building_height <= input_data.mobile_height_m
        ):
            errors.append("COST231-WI NLOS 建筑高度必须大于移动台高度。")
    elif ground_model == "low_band":
        if not 300.0 <= input_data.frequency_mhz <= 500.0:
            errors.append("低频地面模型频率必须在 300 至 500 MHz 之间。")
        reference_distance = params.get("reference_distance_m")
        exponent = params.get("path_loss_exponent")
        minimum = params.get("calibration_min_distance_m")
        maximum = params.get("calibration_max_distance_m")
        if isinstance(reference_distance, int | float) and reference_distance <= 0:
            errors.append("低频地面参考距离必须大于 0 m。")
        if isinstance(exponent, int | float) and exponent <= 0:
            errors.append("低频地面路径损耗指数必须大于 0。")
        if isinstance(minimum, int | float) and minimum <= 0:
            errors.append("低频地面标定最小距离必须大于 0 m。")
        if (
            isinstance(minimum, int | float)
            and isinstance(maximum, int | float)
            and maximum <= minimum
        ):
            errors.append("低频地面标定最大距离必须大于最小距离。")
        if (
            isinstance(reference_distance, int | float)
            and isinstance(minimum, int | float)
            and isinstance(maximum, int | float)
            and not minimum <= reference_distance <= maximum
        ):
            errors.append("低频地面参考距离必须位于标定距离范围内。")
