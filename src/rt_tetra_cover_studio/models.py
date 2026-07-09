from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CalculationInput:
    frequency_mhz: float
    tx_power_dbm: float
    base_antenna_gain_dbi: float
    feeder_loss_db: float
    connector_loss_db: float
    mobile_antenna_gain_dbi: float
    receiver_sensitivity_dbm: float
    base_height_m: float
    mobile_height_m: float
    scenario_type: str
    scenario_params: dict[str, float] = field(default_factory=dict)
    engineering_margin_db: float = 8.0


@dataclass(frozen=True)
class CalculationStep:
    name: str
    formula: str
    substitution: str
    result: float
    unit: str


@dataclass(frozen=True)
class LinkBudgetResult:
    eirp_dbm: float
    max_path_loss_db: float
    steps: list[CalculationStep]


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
    warnings: list[str] = field(default_factory=list)
