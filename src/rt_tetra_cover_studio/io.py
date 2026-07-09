from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CalculationInput


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def calculation_input_from_dict(data: dict[str, Any]) -> CalculationInput:
    return CalculationInput(
        frequency_mhz=float(data["frequency_mhz"]),
        tx_power_dbm=float(data["tx_power_dbm"]),
        base_antenna_gain_dbi=float(data["base_antenna_gain_dbi"]),
        feeder_loss_db=float(data["feeder_loss_db"]),
        connector_loss_db=float(data["connector_loss_db"]),
        mobile_antenna_gain_dbi=float(data["mobile_antenna_gain_dbi"]),
        receiver_sensitivity_dbm=float(data["receiver_sensitivity_dbm"]),
        base_height_m=float(data["base_height_m"]),
        mobile_height_m=float(data["mobile_height_m"]),
        scenario_type=str(data["scenario_type"]),
        scenario_params={key: float(value) for key, value in data["scenario_params"].items()},
        engineering_margin_db=float(data.get("engineering_margin_db", 8.0)),
    )


def load_example_case(path: str | Path) -> dict[str, Any]:
    case_data = load_json(path)
    case_data["calculation_input"] = calculation_input_from_dict(case_data["input"])
    return case_data
