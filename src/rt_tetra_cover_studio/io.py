from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    CalculationInput,
    CalculationResult,
    CalculationStep,
    CurvePoint,
    IterationStep,
    LinkBudgetResult,
)


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


def calculation_input_to_dict(input_data: CalculationInput) -> dict[str, Any]:
    return {
        "frequency_mhz": input_data.frequency_mhz,
        "tx_power_dbm": input_data.tx_power_dbm,
        "base_antenna_gain_dbi": input_data.base_antenna_gain_dbi,
        "feeder_loss_db": input_data.feeder_loss_db,
        "connector_loss_db": input_data.connector_loss_db,
        "mobile_antenna_gain_dbi": input_data.mobile_antenna_gain_dbi,
        "receiver_sensitivity_dbm": input_data.receiver_sensitivity_dbm,
        "base_height_m": input_data.base_height_m,
        "mobile_height_m": input_data.mobile_height_m,
        "scenario_type": input_data.scenario_type,
        "scenario_params": dict(input_data.scenario_params),
        "engineering_margin_db": input_data.engineering_margin_db,
    }


def calculation_result_to_dict(result: CalculationResult) -> dict[str, Any]:
    return {
        "input": calculation_input_to_dict(result.input),
        "summary": {
            "model_name": result.model_name,
            "coverage_distance_m": result.coverage_distance_m,
            "coverage_level": result.coverage_level,
            "eirp_dbm": result.link_budget.eirp_dbm,
            "max_path_loss_db": result.link_budget.max_path_loss_db,
            "boundary_path_loss_db": result.boundary_path_loss_db,
            "boundary_rssi_dbm": result.boundary_rssi_dbm,
            "warnings": list(result.warnings),
        },
        "details": {
            "link_budget": _link_budget_to_dict(result.link_budget),
            "calculation_steps": [_calculation_step_to_dict(step) for step in result.calculation_steps],
            "iteration_steps": [_iteration_step_to_dict(step) for step in result.iteration_steps],
        },
        "charts": {
            "path_loss_curve": [
                {"distance_m": point.distance_m, "path_loss_db": point.path_loss_db}
                for point in result.curve_points
            ],
            "rssi_curve": [
                {"distance_m": point.distance_m, "rssi_dbm": point.rssi_dbm}
                for point in result.curve_points
            ],
            "coverage_boundary": {
                "distance_m": result.coverage_distance_m,
                "path_loss_db": result.boundary_path_loss_db,
                "rssi_dbm": result.boundary_rssi_dbm,
            },
        },
        "report_sections": _report_sections(result),
    }


def save_calculation_result(result: CalculationResult, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(calculation_result_to_dict(result), file, ensure_ascii=False, indent=2)
    return output_path


def _link_budget_to_dict(link_budget: LinkBudgetResult) -> dict[str, Any]:
    return {
        "eirp_dbm": link_budget.eirp_dbm,
        "max_path_loss_db": link_budget.max_path_loss_db,
        "steps": [_calculation_step_to_dict(step) for step in link_budget.steps],
    }


def _calculation_step_to_dict(step: CalculationStep) -> dict[str, Any]:
    return {
        "name": step.name,
        "formula": step.formula,
        "substitution": step.substitution,
        "result": step.result,
        "unit": step.unit,
    }


def _iteration_step_to_dict(step: IterationStep) -> dict[str, Any]:
    return {
        "iteration": step.iteration,
        "distance_m": step.distance_m,
        "path_loss_db": step.path_loss_db,
    }


def _curve_point_to_dict(point: CurvePoint) -> dict[str, Any]:
    return {
        "distance_m": point.distance_m,
        "path_loss_db": point.path_loss_db,
        "rssi_dbm": point.rssi_dbm,
    }


def _report_sections(result: CalculationResult) -> list[dict[str, Any]]:
    return [
        {
            "title": "输入参数",
            "type": "table",
            "data": calculation_input_to_dict(result.input),
        },
        {
            "title": "核心结论",
            "type": "summary",
            "data": {
                "coverage_distance_m": result.coverage_distance_m,
                "coverage_level": result.coverage_level,
                "model_name": result.model_name,
            },
        },
        {
            "title": "链路预算",
            "type": "calculation_steps",
            "data": [_calculation_step_to_dict(step) for step in result.link_budget.steps],
        },
        {
            "title": "覆盖距离求解",
            "type": "iteration_steps",
            "data": [_iteration_step_to_dict(step) for step in result.iteration_steps],
        },
        {
            "title": "曲线数据",
            "type": "curve_points",
            "data": [_curve_point_to_dict(point) for point in result.curve_points],
        },
    ]
