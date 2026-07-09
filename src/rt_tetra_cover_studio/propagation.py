from __future__ import annotations

import math

from .models import CalculationInput, PropagationResult


def _free_space_path_loss_db(frequency_mhz: float, distance_m: float) -> float:
    distance_km = distance_m / 1000.0
    return 32.44 + 20.0 * math.log10(frequency_mhz) + 20.0 * math.log10(distance_km)


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


class TunnelModel:
    name = "Tunnel Model"
    formula_source = "Engineering tunnel path loss model"

    def calculate_path_loss(
        self, input_data: CalculationInput, distance_m: float
    ) -> PropagationResult:
        if distance_m <= 0:
            raise ValueError("distance_m must be greater than 0.")

        alpha_db_per_km = float(input_data.scenario_params.get("alpha_db_per_km", 8.0))
        tunnel_width_m = float(input_data.scenario_params["tunnel_width_m"])
        tunnel_height_m = float(input_data.scenario_params["tunnel_height_m"])
        bend_loss_db = float(input_data.scenario_params.get("bend_loss_db", 0.0))
        section_correction_db = _tunnel_section_correction(tunnel_width_m, tunnel_height_m)
        distance_km = distance_m / 1000.0
        fspl_db = _free_space_path_loss_db(input_data.frequency_mhz, distance_m)
        linear_loss_db = alpha_db_per_km * distance_km
        path_loss_db = fspl_db + linear_loss_db + section_correction_db + bend_loss_db

        return PropagationResult(
            model_name=self.name,
            distance_m=distance_m,
            path_loss_db=path_loss_db,
            formula_source=self.formula_source,
            intermediate_values={
                "fspl_db": fspl_db,
                "linear_loss_db": linear_loss_db,
                "section_correction_db": section_correction_db,
                "bend_loss_db": bend_loss_db,
                "alpha_db_per_km": alpha_db_per_km,
            },
        )


class Cost231WiModel:
    name = "COST231-Walfisch-Ikegami"
    formula_source = "COST231 Walfisch-Ikegami Model"

    def calculate_path_loss(
        self, input_data: CalculationInput, distance_m: float
    ) -> PropagationResult:
        if distance_m <= 0:
            raise ValueError("distance_m must be greater than 0.")

        building_height_m = float(input_data.scenario_params["building_height_m"])
        building_spacing_m = float(input_data.scenario_params["building_spacing_m"])
        street_width_m = float(input_data.scenario_params["street_width_m"])

        fspl_db = _free_space_path_loss_db(input_data.frequency_mhz, distance_m)
        rooftop_to_street_db = _rooftop_to_street_loss(
            frequency_mhz=input_data.frequency_mhz,
            street_width_m=street_width_m,
            building_height_m=building_height_m,
            mobile_height_m=input_data.mobile_height_m,
        )
        multiscreen_db = _multiscreen_loss(
            frequency_mhz=input_data.frequency_mhz,
            distance_m=distance_m,
            building_spacing_m=building_spacing_m,
            building_height_m=building_height_m,
            base_height_m=input_data.base_height_m,
        )
        path_loss_db = fspl_db + rooftop_to_street_db + multiscreen_db

        return PropagationResult(
            model_name=self.name,
            distance_m=distance_m,
            path_loss_db=path_loss_db,
            formula_source=self.formula_source,
            intermediate_values={
                "fspl_db": fspl_db,
                "rooftop_to_street_db": rooftop_to_street_db,
                "multiscreen_db": multiscreen_db,
            },
        )


class ViaductModel:
    name = "COST231-WI + Viaduct Correction"
    formula_source = "COST231-WI with engineering viaduct correction"

    def __init__(self) -> None:
        self._base_model = Cost231WiModel()

    def calculate_path_loss(
        self, input_data: CalculationInput, distance_m: float
    ) -> PropagationResult:
        base_result = self._base_model.calculate_path_loss(input_data, distance_m)
        viaduct_height_m = float(input_data.scenario_params["viaduct_height_m"])
        curve_radius_m = float(input_data.scenario_params.get("curve_radius_m", 0.0))
        height_gain_db = min(viaduct_height_m * 0.25, 8.0)
        curve_loss_db = 0.0 if curve_radius_m <= 0 else min(500.0 / curve_radius_m, 5.0)
        correction_db = curve_loss_db - height_gain_db
        path_loss_db = base_result.path_loss_db + correction_db

        intermediate_values = dict(base_result.intermediate_values)
        intermediate_values.update(
            {
                "viaduct_height_gain_db": height_gain_db,
                "curve_loss_db": curve_loss_db,
                "viaduct_correction_db": correction_db,
            }
        )

        return PropagationResult(
            model_name=self.name,
            distance_m=distance_m,
            path_loss_db=path_loss_db,
            formula_source=self.formula_source,
            intermediate_values=intermediate_values,
        )


def _tunnel_section_correction(tunnel_width_m: float, tunnel_height_m: float) -> float:
    section_area_m2 = max(tunnel_width_m * tunnel_height_m, 1.0)
    return max(12.0 - 2.0 * math.log10(section_area_m2), 0.0)


def _rooftop_to_street_loss(
    *,
    frequency_mhz: float,
    street_width_m: float,
    building_height_m: float,
    mobile_height_m: float,
) -> float:
    width = max(street_width_m, 1.0)
    height_delta = max(building_height_m - mobile_height_m, 1.0)
    return -16.9 - 10.0 * math.log10(width) + 10.0 * math.log10(frequency_mhz) + (
        20.0 * math.log10(height_delta)
    )


def _multiscreen_loss(
    *,
    frequency_mhz: float,
    distance_m: float,
    building_spacing_m: float,
    building_height_m: float,
    base_height_m: float,
) -> float:
    distance_km = max(distance_m / 1000.0, 0.001)
    spacing = max(building_spacing_m, 1.0)
    height_delta = base_height_m - building_height_m
    base_station_height_loss_db = -18.0 * math.log10(1.0 + max(height_delta, 0.0))
    distance_factor_db = 18.0 * math.log10(distance_km)
    frequency_factor_db = -4.0 + 0.7 * ((frequency_mhz / 925.0) - 1.0)
    spacing_loss_db = -9.0 * math.log10(spacing)
    return base_station_height_loss_db + distance_factor_db + frequency_factor_db + spacing_loss_db + 54.0


def get_model(scenario_type: str) -> ItuIndoorModel | TunnelModel | Cost231WiModel | ViaductModel:
    if scenario_type == "underground":
        return ItuIndoorModel()
    if scenario_type == "tunnel":
        return TunnelModel()
    if scenario_type == "ground":
        return Cost231WiModel()
    if scenario_type == "viaduct":
        return ViaductModel()
    raise ValueError(f"Unsupported scenario_type: {scenario_type}")
