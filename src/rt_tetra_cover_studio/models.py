from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CalculationInput:
    frequency_mhz: float
    base_tx_power_w: float
    mobile_tx_power_w: float
    base_antenna_gain_dbi: float
    base_feeder_loss_db: float
    base_other_loss_db: float
    mobile_antenna_gain_dbi: float
    body_loss_db: float
    mobile_receiver_sensitivity_dbm: float
    base_receiver_sensitivity_dbm: float
    base_diversity_gain_db: float
    shadow_fading_std_db: float
    edge_coverage_probability_pct: float
    interference_margin_db: float
    penetration_loss_db: float
    base_height_m: float
    mobile_height_m: float
    scenario_type: str
    scenario_params: dict[str, float] = field(default_factory=dict)

@dataclass(frozen=True)
class CalculationStep:
    name: str
    formula: str
    substitution: str
    result: float
    unit: str


@dataclass(frozen=True)
class LinkBudgetResult:
    base_eirp_dbm: float
    mobile_eirp_dbm: float
    shadow_fading_margin_db: float
    required_rx_mobile_dbm: float
    required_rx_base_dbm: float
    downlink_mapl_db: float
    uplink_mapl_db: float
    max_path_loss_db: float
    limiting_link: str
    steps: list[CalculationStep]

@dataclass(frozen=True)
class CalculationDetail:
    name: str
    formula: str
    substitution: str
    result: str


@dataclass(frozen=True)
class CalculationSection:
    number: int
    title: str
    description: str
    details: list[CalculationDetail]


@dataclass(frozen=True)
class PropagationResult:
    model_name: str
    distance_m: float
    path_loss_db: float
    formula_source: str
    intermediate_values: dict[str, float]


@dataclass(frozen=True)
class IterationStep:
    iteration: int
    distance_m: float
    path_loss_db: float


@dataclass(frozen=True)
class CurvePoint:
    distance_m: float
    path_loss_db: float
    rssi_dbm: float


@dataclass(frozen=True)
class CalculationResult:
    input: CalculationInput
    link_budget: LinkBudgetResult
    model_name: str
    coverage_distance_m: float
    coverage_level: str
    boundary_path_loss_db: float
    boundary_rssi_dbm: float
    iteration_steps: list[IterationStep]
    curve_points: list[CurvePoint]
    calculation_steps: list[CalculationStep]
    calculation_sections: list[CalculationSection]
    warnings: list[str] = field(default_factory=list)
