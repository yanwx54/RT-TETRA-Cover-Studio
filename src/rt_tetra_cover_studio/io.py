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
        base_tx_power_w=float(data["base_tx_power_w"]),
        mobile_tx_power_w=float(data["mobile_tx_power_w"]),
        base_antenna_gain_dbi=float(data["base_antenna_gain_dbi"]),
        base_feeder_loss_db=float(data["base_feeder_loss_db"]),
        base_other_loss_db=float(data["base_other_loss_db"]),
        mobile_antenna_gain_dbi=float(data["mobile_antenna_gain_dbi"]),
        body_loss_db=float(data["body_loss_db"]),
        mobile_receiver_sensitivity_dbm=float(data["mobile_receiver_sensitivity_dbm"]),
        base_receiver_sensitivity_dbm=float(data["base_receiver_sensitivity_dbm"]),
        base_diversity_gain_db=float(data["base_diversity_gain_db"]),
        shadow_fading_std_db=float(data["shadow_fading_std_db"]),
        edge_coverage_probability_pct=float(data["edge_coverage_probability_pct"]),
        interference_margin_db=float(data["interference_margin_db"]),
        penetration_loss_db=float(data["penetration_loss_db"]),
        base_height_m=float(data["base_height_m"]),
        mobile_height_m=float(data["mobile_height_m"]),
        scenario_type=str(data["scenario_type"]),
        scenario_params={
            key: str(value) if isinstance(value, str) else float(value)
            for key, value in data["scenario_params"].items()
        },
    )


def load_example_case(path: str | Path) -> dict[str, Any]:
    case_data = load_json(path)
    case_data["calculation_input"] = calculation_input_from_dict(case_data["input"])
    return case_data


def calculation_input_to_dict(input_data: CalculationInput) -> dict[str, Any]:
    return {
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
        "scenario_type": input_data.scenario_type,
        "scenario_params": dict(input_data.scenario_params),
    }


def calculation_result_to_dict(result: CalculationResult) -> dict[str, Any]:
    return {
        "input": calculation_input_to_dict(result.input),
        "summary": {
            "model_name": result.model_name,
            "coverage_distance_m": result.coverage_distance_m,
            "coverage_level": result.coverage_level,
            "eirp_dbm": result.link_budget.base_eirp_dbm,
            "base_eirp_dbm": result.link_budget.base_eirp_dbm,
            "mobile_eirp_dbm": result.link_budget.mobile_eirp_dbm,
            "max_path_loss_db": result.link_budget.max_path_loss_db,
            "downlink_mapl_db": result.link_budget.downlink_mapl_db,
            "uplink_mapl_db": result.link_budget.uplink_mapl_db,
            "limiting_link": result.link_budget.limiting_link,
            "calibration_status": result.input.scenario_params.get(
                "calibration_status", "not_applicable"
            ),
            "calibration_source": result.input.scenario_params.get(
                "calibration_source", ""
            ),
            "boundary_path_loss_db": result.boundary_path_loss_db,
            "boundary_rssi_dbm": result.boundary_rssi_dbm,
            "warnings": list(result.warnings),
        },
        "details": {
            "link_budget": _link_budget_to_dict(result.link_budget),
            "calculation_steps": [_calculation_step_to_dict(step) for step in result.calculation_steps],
            "iteration_steps": [_iteration_step_to_dict(step) for step in result.iteration_steps],
            "calculation_sections": [
                {
                    "number": section.number,
                    "title": section.title,
                    "description": section.description,
                    "details": [
                        {
                            "name": detail.name,
                            "formula": detail.formula,
                            "substitution": detail.substitution,
                            "result": detail.result,
                        }
                        for detail in section.details
                    ],
                }
                for section in result.calculation_sections
            ],
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
        "eirp_dbm": link_budget.base_eirp_dbm,
        "base_eirp_dbm": link_budget.base_eirp_dbm,
        "mobile_eirp_dbm": link_budget.mobile_eirp_dbm,
        "shadow_fading_margin_db": link_budget.shadow_fading_margin_db,
        "required_rx_mobile_dbm": link_budget.required_rx_mobile_dbm,
        "required_rx_base_dbm": link_budget.required_rx_base_dbm,
        "downlink_mapl_db": link_budget.downlink_mapl_db,
        "uplink_mapl_db": link_budget.uplink_mapl_db,
        "max_path_loss_db": link_budget.max_path_loss_db,
        "limiting_link": link_budget.limiting_link,
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
                "calibration_status": result.input.scenario_params.get(
                    "calibration_status", "not_applicable"
                ),
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
