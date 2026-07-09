from __future__ import annotations

from .models import CalculationInput


SUPPORTED_SCENARIOS = {"underground"}


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
        errors.append("当前最小闭环仅支持 underground 场景。")

    return errors
