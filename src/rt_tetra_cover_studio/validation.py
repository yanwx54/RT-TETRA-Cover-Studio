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
    if input_data.feeder_loss_db < 0:
        errors.append("馈线损耗不能小于 0 dB。")
    if input_data.connector_loss_db < 0:
        errors.append("接头损耗不能小于 0 dB。")
    if input_data.engineering_margin_db < 0:
        errors.append("工程裕度不能小于 0 dB。")
    if input_data.receiver_sensitivity_dbm >= 0:
        errors.append("接收灵敏度应为负 dBm 值。")
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
