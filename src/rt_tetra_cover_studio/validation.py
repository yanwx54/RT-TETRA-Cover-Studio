from __future__ import annotations

from .models import CalculationInput


SUPPORTED_SCENARIOS = {"underground", "tunnel", "ground", "viaduct"}

REQUIRED_SCENARIO_PARAMS = {
    "underground": set(),
    "tunnel": {"tunnel_width_m", "tunnel_height_m"},
    "ground": {"building_height_m", "building_spacing_m", "street_width_m"},
    "viaduct": {
        "building_height_m",
        "building_spacing_m",
        "street_width_m",
        "viaduct_height_m",
    },
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
        missing_params = REQUIRED_SCENARIO_PARAMS[input_data.scenario_type] - set(
            input_data.scenario_params
        )
        if missing_params:
            errors.append(f"场景参数缺失：{', '.join(sorted(missing_params))}。")

    for name, value in input_data.scenario_params.items():
        if isinstance(value, int | float) and value < 0:
            errors.append(f"场景参数 {name} 不能小于 0。")

    return errors
