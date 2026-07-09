from __future__ import annotations

import math

from .models import CalculationInput, PropagationResult


class ItuIndoorModel:
    name = "ITU Indoor"
    formula_source = "ITU-R P.1238 Indoor Propagation"

    def calculate_path_loss(
        self, input_data: CalculationInput, distance_m: float
    ) -> PropagationResult:
        if distance_m <= 0:
            raise ValueError("distance_m must be greater than 0.")

        n = float(input_data.scenario_params.get("distance_power_loss_coefficient", 40.0))
        wall_loss_db = float(input_data.scenario_params.get("wall_loss_db", 0.0))
        floor_loss_db = float(input_data.scenario_params.get("floor_loss_db", 0.0))

        frequency_term_db = 20.0 * math.log10(input_data.frequency_mhz)
        distance_term_db = n * math.log10(distance_m)
        path_loss_db = frequency_term_db + distance_term_db + wall_loss_db + floor_loss_db - 28.0

        return PropagationResult(
            model_name=self.name,
            distance_m=distance_m,
            path_loss_db=path_loss_db,
            formula_source=self.formula_source,
            intermediate_values={
                "frequency_term_db": frequency_term_db,
                "distance_term_db": distance_term_db,
                "wall_loss_db": wall_loss_db,
                "floor_loss_db": floor_loss_db,
                "distance_power_loss_coefficient": n,
            },
        )


def get_model(scenario_type: str) -> ItuIndoorModel:
    if scenario_type == "underground":
        return ItuIndoorModel()
    raise ValueError(f"Unsupported scenario_type: {scenario_type}")
