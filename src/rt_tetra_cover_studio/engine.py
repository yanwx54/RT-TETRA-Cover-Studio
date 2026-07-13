from __future__ import annotations

import math
from statistics import NormalDist

from .models import (
    CalculationDetail,
    CalculationInput,
    CalculationResult,
    CalculationSection,
    CalculationStep,
    CurvePoint,
    IterationStep,
    LinkBudgetResult,
    PropagationResult,
)
from .propagation import get_model, model_distance_bounds
from .validation import validate_input


def calculate_link_budget(input_data: CalculationInput) -> LinkBudgetResult:
    base_tx_power_dbm = _watts_to_dbm(input_data.base_tx_power_w)
    mobile_tx_power_dbm = _watts_to_dbm(input_data.mobile_tx_power_w)
    base_eirp_dbm = (
        base_tx_power_dbm
        + input_data.base_antenna_gain_dbi
        - input_data.base_feeder_loss_db
        - input_data.base_other_loss_db
    )
    mobile_eirp_dbm = (
        mobile_tx_power_dbm
        + input_data.mobile_antenna_gain_dbi
        - input_data.body_loss_db
    )
    coverage_probability = input_data.edge_coverage_probability_pct / 100.0
    z_score = NormalDist().inv_cdf(coverage_probability)
    shadow_fading_margin_db = z_score * input_data.shadow_fading_std_db

    required_rx_mobile_dbm = (
        input_data.mobile_receiver_sensitivity_dbm
        + input_data.body_loss_db
        - input_data.mobile_antenna_gain_dbi
        + shadow_fading_margin_db
        + input_data.interference_margin_db
        + input_data.penetration_loss_db
    )
    required_rx_base_dbm = (
        input_data.base_receiver_sensitivity_dbm
        - input_data.base_antenna_gain_dbi
        + input_data.base_feeder_loss_db
        + input_data.base_other_loss_db
        - input_data.base_diversity_gain_db
        + shadow_fading_margin_db
        + input_data.interference_margin_db
        + input_data.penetration_loss_db
    )
    downlink_mapl_db = base_eirp_dbm - required_rx_mobile_dbm
    uplink_mapl_db = mobile_eirp_dbm - required_rx_base_dbm
    max_path_loss_db = min(downlink_mapl_db, uplink_mapl_db)
    limiting_link = "下行" if downlink_mapl_db <= uplink_mapl_db else "上行"

    steps = [
        CalculationStep(
            name="基站 EIRP",
            formula="P_BS(dBm) + G_BS - L_feeder - L_other",
            substitution=(
                f"{base_tx_power_dbm:.2f} + {input_data.base_antenna_gain_dbi} "
                f"- {input_data.base_feeder_loss_db} - {input_data.base_other_loss_db}"
            ),
            result=base_eirp_dbm,
            unit="dBm",
        ),
        CalculationStep(
            name="移动台 EIRP",
            formula="P_MS(dBm) + G_MS - L_body",
            substitution=(
                f"{mobile_tx_power_dbm:.2f} + {input_data.mobile_antenna_gain_dbi} "
                f"- {input_data.body_loss_db}"
            ),
            result=mobile_eirp_dbm,
            unit="dBm",
        ),
        CalculationStep(
            name="阴影衰落余量",
            formula="Z(p) × σ",
            substitution=f"{z_score:.3f} × {input_data.shadow_fading_std_db}",
            result=shadow_fading_margin_db,
            unit="dB",
        ),
        CalculationStep(
            name="下行 MAPL",
            formula="EIRP_BS - Req_Rx_MS",
            substitution=f"{base_eirp_dbm:.2f} - ({required_rx_mobile_dbm:.2f})",
            result=downlink_mapl_db,
            unit="dB",
        ),
        CalculationStep(
            name="上行 MAPL",
            formula="EIRP_MS - Req_Rx_BS",
            substitution=f"{mobile_eirp_dbm:.2f} - ({required_rx_base_dbm:.2f})",
            result=uplink_mapl_db,
            unit="dB",
        ),
    ]

    return LinkBudgetResult(
        base_eirp_dbm=base_eirp_dbm,
        mobile_eirp_dbm=mobile_eirp_dbm,
        shadow_fading_margin_db=shadow_fading_margin_db,
        required_rx_mobile_dbm=required_rx_mobile_dbm,
        required_rx_base_dbm=required_rx_base_dbm,
        downlink_mapl_db=downlink_mapl_db,
        uplink_mapl_db=uplink_mapl_db,
        max_path_loss_db=max_path_loss_db,
        limiting_link=limiting_link,
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
    model = get_model(input_data)
    warnings: list[str] = []
    model_min_distance_m, model_max_distance_m = model_distance_bounds(input_data)
    search_min_distance_m = max(min_distance_m, model_min_distance_m)
    search_max_distance_m = min(max_distance_m, model_max_distance_m)
    if search_min_distance_m >= search_max_distance_m:
        raise ValueError("计算距离范围与传播模型适用范围没有交集。")
    if search_min_distance_m != min_distance_m or search_max_distance_m != max_distance_m:
        warnings.append(
            "搜索距离已限制在模型适用范围 "
            f"{search_min_distance_m:.1f} 至 {search_max_distance_m:.1f} m。"
        )
    if input_data.scenario_params.get("calibration_status") == "unverified":
        warnings.append("当前模型参数未经现场数据校准，结果仅用于初步估算。")

    low_loss = model.calculate_path_loss(input_data, search_min_distance_m).path_loss_db
    high_loss = model.calculate_path_loss(input_data, search_max_distance_m).path_loss_db

    if low_loss > link_budget.max_path_loss_db:
        coverage_distance_m = search_min_distance_m
        warnings.append("最小计算距离已超过最大允许路径损耗。")
        iteration_steps = [IterationStep(0, search_min_distance_m, low_loss)]
    elif high_loss <= link_budget.max_path_loss_db:
        coverage_distance_m = search_max_distance_m
        warnings.append("覆盖距离达到模型或搜索距离上限。")
        iteration_steps = [IterationStep(0, search_max_distance_m, high_loss)]
    else:
        coverage_distance_m, iteration_steps = _solve_coverage_distance(
            input_data=input_data,
            max_path_loss_db=link_budget.max_path_loss_db,
            min_distance_m=search_min_distance_m,
            max_distance_m=search_max_distance_m,
            tolerance_m=tolerance_m,
            max_iterations=max_iterations,
        )

    boundary = model.calculate_path_loss(input_data, coverage_distance_m)
    boundary_rssi_dbm = _calculate_downlink_rssi(
        input_data=input_data,
        base_eirp_dbm=link_budget.base_eirp_dbm,
        path_loss_db=boundary.path_loss_db,
    )

    return CalculationResult(
        input=input_data,
        link_budget=link_budget,
        model_name=boundary.model_name,
        coverage_distance_m=coverage_distance_m,
        coverage_level=_coverage_level(boundary_rssi_dbm),
        boundary_path_loss_db=boundary.path_loss_db,
        boundary_rssi_dbm=boundary_rssi_dbm,
        iteration_steps=iteration_steps,
        curve_points=_build_curve_points(
            input_data,
            link_budget.base_eirp_dbm,
            coverage_distance_m,
            curve_points,
            search_min_distance_m,
        ),
        calculation_steps=link_budget.steps,
        calculation_sections=_build_calculation_sections(
            input_data=input_data,
            link_budget=link_budget,
            boundary=boundary,
            coverage_distance_m=coverage_distance_m,
            iteration_steps=iteration_steps,
        ),
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
    model = get_model(input_data)
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
    base_eirp_dbm: float,
    coverage_distance_m: float,
    point_count: int,
    start_distance_m: float,
) -> list[CurvePoint]:
    model = get_model(input_data)
    safe_count = max(point_count, 2)
    step_m = max(coverage_distance_m - start_distance_m, 0.0) / (safe_count - 1)
    points: list[CurvePoint] = []

    for index in range(safe_count):
        distance_m = start_distance_m + step_m * index
        path_loss_db = model.calculate_path_loss(input_data, distance_m).path_loss_db
        points.append(
            CurvePoint(
                distance_m=distance_m,
                path_loss_db=path_loss_db,
                rssi_dbm=_calculate_downlink_rssi(
                    input_data=input_data,
                    base_eirp_dbm=base_eirp_dbm,
                    path_loss_db=path_loss_db,
                ),
            )
        )

    return points


def _watts_to_dbm(power_w: float) -> float:
    return 10.0 * math.log10(power_w * 1000.0)


def _calculate_downlink_rssi(
    *,
    input_data: CalculationInput,
    base_eirp_dbm: float,
    path_loss_db: float,
) -> float:
    return (
        base_eirp_dbm
        - path_loss_db
        + input_data.mobile_antenna_gain_dbi
        - input_data.body_loss_db
        - input_data.penetration_loss_db
    )


def _build_calculation_sections(
    *,
    input_data: CalculationInput,
    link_budget: LinkBudgetResult,
    boundary: PropagationResult,
    coverage_distance_m: float,
    iteration_steps: list[IterationStep],
) -> list[CalculationSection]:
    base_tx_power_dbm = _watts_to_dbm(input_data.base_tx_power_w)
    mobile_tx_power_dbm = _watts_to_dbm(input_data.mobile_tx_power_w)
    probability = input_data.edge_coverage_probability_pct / 100.0
    z_score = NormalDist().inv_cdf(probability)

    return [
        CalculationSection(
            number=1,
            title="有效全向辐射功率 (EIRP) 计算",
            description="EIRP 表示发射端在理想全向天线方向上辐射的等效功率。",
            details=[
                CalculationDetail(
                    name="基站 (BS) EIRP",
                    formula="EIRP_BS = P_BS(dBm) + G_BS - L_feeder - L_other",
                    substitution=(
                        f"EIRP_BS = {base_tx_power_dbm:.2f} + "
                        f"{input_data.base_antenna_gain_dbi:.2f} - "
                        f"{input_data.base_feeder_loss_db:.2f} - "
                        f"{input_data.base_other_loss_db:.2f}"
                    ),
                    result=f"EIRP_BS = {link_budget.base_eirp_dbm:.2f} dBm",
                ),
                CalculationDetail(
                    name="移动台 (MS) EIRP",
                    formula="EIRP_MS = P_MS(dBm) + G_MS - L_body",
                    substitution=(
                        f"EIRP_MS = {mobile_tx_power_dbm:.2f} + "
                        f"{input_data.mobile_antenna_gain_dbi:.2f} - "
                        f"{input_data.body_loss_db:.2f}"
                    ),
                    result=f"EIRP_MS = {link_budget.mobile_eirp_dbm:.2f} dBm",
                ),
            ],
        ),
        CalculationSection(
            number=2,
            title="最低要求接收功率计算",
            description=(
                "接收功率必须达到接收灵敏度，并预留地点覆盖概率对应的阴影衰落余量、"
                "干扰余量和穿透损耗。"
            ),
            details=[
                CalculationDetail(
                    name="阴影衰落余量",
                    formula="M_shadow = Z(p) × σ",
                    substitution=(
                        f"M_shadow = {z_score:.3f} × {input_data.shadow_fading_std_db:.2f} "
                        f"(p = {input_data.edge_coverage_probability_pct:.2f}%)"
                    ),
                    result=f"M_shadow = {link_budget.shadow_fading_margin_db:.2f} dB",
                ),
                CalculationDetail(
                    name="移动台 (MS) 最低要求接收功率（下行）",
                    formula="Req_Rx_MS = Sens_MS + L_body - G_MS + M_shadow + M_int + L_pen",
                    substitution=(
                        f"Req_Rx_MS = ({input_data.mobile_receiver_sensitivity_dbm:.2f}) + "
                        f"{input_data.body_loss_db:.2f} - {input_data.mobile_antenna_gain_dbi:.2f} + "
                        f"{link_budget.shadow_fading_margin_db:.2f} + "
                        f"{input_data.interference_margin_db:.2f} + {input_data.penetration_loss_db:.2f}"
                    ),
                    result=f"Req_Rx_MS = {link_budget.required_rx_mobile_dbm:.2f} dBm",
                ),
                CalculationDetail(
                    name="基站 (BS) 最低要求接收功率（上行）",
                    formula=(
                        "Req_Rx_BS = Sens_BS - G_BS + L_feeder + L_other - G_div "
                        "+ M_shadow + M_int + L_pen"
                    ),
                    substitution=(
                        f"Req_Rx_BS = ({input_data.base_receiver_sensitivity_dbm:.2f}) - "
                        f"{input_data.base_antenna_gain_dbi:.2f} + "
                        f"{input_data.base_feeder_loss_db:.2f} + {input_data.base_other_loss_db:.2f} - "
                        f"{input_data.base_diversity_gain_db:.2f} + "
                        f"{link_budget.shadow_fading_margin_db:.2f} + "
                        f"{input_data.interference_margin_db:.2f} + {input_data.penetration_loss_db:.2f}"
                    ),
                    result=f"Req_Rx_BS = {link_budget.required_rx_base_dbm:.2f} dBm",
                ),
            ],
        ),
        CalculationSection(
            number=3,
            title="最大允许路径损耗 (MAPL)",
            description="系统覆盖由上下行 MAPL 中较小的一方决定。",
            details=[
                CalculationDetail(
                    name="下行链路 MAPL",
                    formula="MAPL_DL = EIRP_BS - Req_Rx_MS",
                    substitution=(
                        f"MAPL_DL = {link_budget.base_eirp_dbm:.2f} - "
                        f"({link_budget.required_rx_mobile_dbm:.2f})"
                    ),
                    result=f"MAPL_DL = {link_budget.downlink_mapl_db:.2f} dB",
                ),
                CalculationDetail(
                    name="上行链路 MAPL",
                    formula="MAPL_UL = EIRP_MS - Req_Rx_BS",
                    substitution=(
                        f"MAPL_UL = {link_budget.mobile_eirp_dbm:.2f} - "
                        f"({link_budget.required_rx_base_dbm:.2f})"
                    ),
                    result=f"MAPL_UL = {link_budget.uplink_mapl_db:.2f} dB",
                ),
                CalculationDetail(
                    name="系统 MAPL",
                    formula="MAPL = min(MAPL_DL, MAPL_UL)",
                    substitution=(
                        f"MAPL = min({link_budget.downlink_mapl_db:.2f}, "
                        f"{link_budget.uplink_mapl_db:.2f})"
                    ),
                    result=(
                        f"系统 MAPL = {link_budget.max_path_loss_db:.2f} dB，"
                        f"{link_budget.limiting_link}受限"
                    ),
                ),
            ],
        ),
        _build_model_section(input_data, boundary),
        CalculationSection(
            number=5,
            title="覆盖距离求解",
            description="使用当前传播模型的数值反解，以系统 MAPL 为路径损耗上限。",
            details=[
                CalculationDetail(
                    name="求解目标",
                    formula="PathLoss(d) = System MAPL",
                    substitution=(
                        f"PathLoss(d) = {link_budget.max_path_loss_db:.2f} dB，"
                        f"二分法迭代 {len(iteration_steps)} 次"
                    ),
                    result=f"最大覆盖距离 = {coverage_distance_m:.1f} m",
                )
            ],
        ),
    ]


def _build_model_section(
    input_data: CalculationInput, boundary: PropagationResult
) -> CalculationSection:
    formulas = {
        "ITU Indoor": "L = 20log10(f_MHz) + Nlog10(d_m) + L_wall + L_floor - 28",
        "Tunnel Model": (
            "L = FSPL + αd_km + K_section + L_bend + L_train + K_cal"
        ),
        "Low-Band Calibrated Ground": (
            "L = FSPL(f,d0) + 10nlog10(d/d0) + K_cal"
        ),
        "COST231-Walfisch-Ikegami": (
            "LOS: L = 42.6 + 26log10(d_km) + 20log10(f_MHz); "
            "NLOS: L = L0 + max(Lrts + Lmsd, 0); "
            "Lrts = -16.9 - 10log10(w) + 10log10(f) + 20log10(Δhm) + Lori; "
            "Lmsd = Lbsh + ka + kdlog10(d_km) + kflog10(f) - 9log10(b)"
        ),
    }
    values = ", ".join(
        f"{name}={value:.4f}" if isinstance(value, int | float) else f"{name}={value}"
        for name, value in boundary.intermediate_values.items()
    )
    return CalculationSection(
        number=4,
        title=f"{boundary.model_name} 传播模型参数与公式",
        description=f"公式来源：{boundary.formula_source}",
        details=[
            CalculationDetail(
                name="核心公式与中间量",
                formula=(
                    "L = L_ground + K_viaduct + L_train + K_cal"
                    if input_data.scenario_type == "viaduct"
                    else formulas[boundary.model_name]
                ),
                substitution=(
                    f"f={input_data.frequency_mhz:.2f} MHz，d={boundary.distance_m:.1f} m；{values}"
                ),
                result=f"Path Loss = {boundary.path_loss_db:.2f} dB",
            )
        ],
    )


def _coverage_level(rssi_dbm: float) -> str:
    if rssi_dbm >= -85.0:
        return "优"
    if rssi_dbm >= -95.0:
        return "良"
    if rssi_dbm >= -105.0:
        return "可用"
    return "边缘覆盖"
