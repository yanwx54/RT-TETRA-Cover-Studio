from __future__ import annotations

from .models import (
    CalculationInput,
    CalculationResult,
    CalculationStep,
    CurvePoint,
    IterationStep,
    LinkBudgetResult,
)
from .propagation import get_model
from .validation import validate_input


def calculate_link_budget(input_data: CalculationInput) -> LinkBudgetResult:
    eirp_dbm = (
        input_data.tx_power_dbm
        + input_data.base_antenna_gain_dbi
        - input_data.feeder_loss_db
        - input_data.connector_loss_db
    )
    max_path_loss_db = (
        eirp_dbm
        + input_data.mobile_antenna_gain_dbi
        - input_data.receiver_sensitivity_dbm
        - input_data.engineering_margin_db
    )

    steps = [
        CalculationStep(
            name="EIRP",
            formula="TxPower + BaseAntennaGain - FeederLoss - ConnectorLoss",
            substitution=(
                f"{input_data.tx_power_dbm} + {input_data.base_antenna_gain_dbi} "
                f"- {input_data.feeder_loss_db} - {input_data.connector_loss_db}"
            ),
            result=eirp_dbm,
            unit="dBm",
        ),
        CalculationStep(
            name="Maximum Path Loss",
            formula="EIRP + MobileAntennaGain - ReceiverSensitivity - EngineeringMargin",
            substitution=(
                f"{eirp_dbm} + {input_data.mobile_antenna_gain_dbi} "
                f"- ({input_data.receiver_sensitivity_dbm}) - {input_data.engineering_margin_db}"
            ),
            result=max_path_loss_db,
            unit="dB",
        ),
    ]

    return LinkBudgetResult(
        eirp_dbm=eirp_dbm,
        max_path_loss_db=max_path_loss_db,
        steps=steps,
    )


def calculate_coverage(
    input_data: CalculationInput,
    *,
    min_distance_m: float = 1.0,
    max_distance_m: float = 50_000.0,
    tolerance_m: float = 1.0,
    max_iterations: int = 100,
    curve_points: int = 50,
) -> CalculationResult:
    errors = validate_input(input_data)
    if errors:
        raise ValueError("; ".join(errors))

    link_budget = calculate_link_budget(input_data)
    model = get_model(input_data.scenario_type)
    warnings: list[str] = []

    low_loss = model.calculate_path_loss(input_data, min_distance_m).path_loss_db
    high_loss = model.calculate_path_loss(input_data, max_distance_m).path_loss_db

    if low_loss > link_budget.max_path_loss_db:
        coverage_distance_m = min_distance_m
        warnings.append("最小计算距离已超过最大允许路径损耗。")
        iteration_steps = [IterationStep(0, min_distance_m, low_loss)]
    elif high_loss <= link_budget.max_path_loss_db:
        coverage_distance_m = max_distance_m
        warnings.append("覆盖距离达到最大搜索上限。")
        iteration_steps = [IterationStep(0, max_distance_m, high_loss)]
    else:
        coverage_distance_m, iteration_steps = _solve_coverage_distance(
            input_data=input_data,
            max_path_loss_db=link_budget.max_path_loss_db,
            min_distance_m=min_distance_m,
            max_distance_m=max_distance_m,
            tolerance_m=tolerance_m,
            max_iterations=max_iterations,
        )

    boundary = model.calculate_path_loss(input_data, coverage_distance_m)
    boundary_rssi_dbm = _calculate_rssi(
        eirp_dbm=link_budget.eirp_dbm,
        mobile_antenna_gain_dbi=input_data.mobile_antenna_gain_dbi,
        path_loss_db=boundary.path_loss_db,
    )

    return CalculationResult(
        input=input_data,
        link_budget=link_budget,
        model_name=model.name,
        coverage_distance_m=coverage_distance_m,
        coverage_level=_coverage_level(boundary_rssi_dbm),
        boundary_path_loss_db=boundary.path_loss_db,
        boundary_rssi_dbm=boundary_rssi_dbm,
        iteration_steps=iteration_steps,
        curve_points=_build_curve_points(input_data, link_budget.eirp_dbm, coverage_distance_m, curve_points),
        calculation_steps=link_budget.steps,
        warnings=warnings,
    )


def _solve_coverage_distance(
    *,
    input_data: CalculationInput,
    max_path_loss_db: float,
    min_distance_m: float,
    max_distance_m: float,
    tolerance_m: float,
    max_iterations: int,
) -> tuple[float, list[IterationStep]]:
    model = get_model(input_data.scenario_type)
    low = min_distance_m
    high = max_distance_m
    steps: list[IterationStep] = []

    for iteration in range(1, max_iterations + 1):
        mid = (low + high) / 2.0
        path_loss_db = model.calculate_path_loss(input_data, mid).path_loss_db
        steps.append(IterationStep(iteration, mid, path_loss_db))

        if path_loss_db <= max_path_loss_db:
            low = mid
        else:
            high = mid

        if high - low <= tolerance_m:
            break

    return low, steps


def _build_curve_points(
    input_data: CalculationInput,
    eirp_dbm: float,
    coverage_distance_m: float,
    point_count: int,
) -> list[CurvePoint]:
    model = get_model(input_data.scenario_type)
    safe_count = max(point_count, 2)
    step_m = max(coverage_distance_m - 1.0, 1.0) / (safe_count - 1)
    points: list[CurvePoint] = []

    for index in range(safe_count):
        distance_m = 1.0 + step_m * index
        path_loss_db = model.calculate_path_loss(input_data, distance_m).path_loss_db
        points.append(
            CurvePoint(
                distance_m=distance_m,
                path_loss_db=path_loss_db,
                rssi_dbm=_calculate_rssi(
                    eirp_dbm=eirp_dbm,
                    mobile_antenna_gain_dbi=input_data.mobile_antenna_gain_dbi,
                    path_loss_db=path_loss_db,
                ),
            )
        )

    return points


def _calculate_rssi(
    *,
    eirp_dbm: float,
    mobile_antenna_gain_dbi: float,
    path_loss_db: float,
) -> float:
    return eirp_dbm + mobile_antenna_gain_dbi - path_loss_db


def _coverage_level(rssi_dbm: float) -> str:
    if rssi_dbm >= -85.0:
        return "优"
    if rssi_dbm >= -95.0:
        return "良"
    if rssi_dbm >= -105.0:
        return "可用"
    return "边缘覆盖"
