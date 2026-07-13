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
        bend_loss_db = float(input_data.scenario_params.get("bend_loss_db", 0.0))
        section_correction_db = float(
            input_data.scenario_params.get("section_correction_db", 0.0)
        )
        train_blockage_loss_db = float(
            input_data.scenario_params.get("train_blockage_loss_db", 0.0)
        )
        calibration_offset_db = float(
            input_data.scenario_params.get("calibration_offset_db", 0.0)
        )
        distance_km = distance_m / 1000.0
        fspl_db = _free_space_path_loss_db(input_data.frequency_mhz, distance_m)
        linear_loss_db = alpha_db_per_km * distance_km
        path_loss_db = (
            fspl_db
            + linear_loss_db
            + section_correction_db
            + bend_loss_db
            + train_blockage_loss_db
            + calibration_offset_db
        )

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
                "train_blockage_loss_db": train_blockage_loss_db,
                "calibration_offset_db": calibration_offset_db,
                "alpha_db_per_km": alpha_db_per_km,
                "calibration_status": str(
                    input_data.scenario_params.get("calibration_status", "unverified")
                ),
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
        if not 20.0 <= distance_m <= 5000.0:
            raise ValueError("COST231-WI distance must be between 20 m and 5000 m.")
        if not 800.0 <= input_data.frequency_mhz <= 2000.0:
            raise ValueError("COST231-WI frequency must be between 800 MHz and 2000 MHz.")
        if not 4.0 <= input_data.base_height_m <= 50.0:
            raise ValueError("COST231-WI base height must be between 4 m and 50 m.")
        if not 1.0 <= input_data.mobile_height_m <= 3.0:
            raise ValueError("COST231-WI mobile height must be between 1 m and 3 m.")

        building_height_m = float(input_data.scenario_params["building_height_m"])
        building_spacing_m = float(input_data.scenario_params["building_spacing_m"])
        street_width_m = float(input_data.scenario_params["street_width_m"])
        street_orientation_deg = float(
            input_data.scenario_params["street_orientation_deg"]
        )
        propagation_condition = str(
            input_data.scenario_params["propagation_condition"]
        ).lower()
        city_type = str(input_data.scenario_params["city_type"]).lower()
        model_correction_db = float(
            input_data.scenario_params.get("model_correction_db", 0.0)
        )
        distance_km = distance_m / 1000.0
        if propagation_condition not in {"los", "nlos"}:
            raise ValueError("propagation_condition must be los or nlos.")
        if city_type not in {"medium", "metropolitan"}:
            raise ValueError("city_type must be medium or metropolitan.")

        if propagation_condition == "los":
            distance_term_db = 26.0 * math.log10(distance_km)
            frequency_term_db = 20.0 * math.log10(input_data.frequency_mhz)
            path_loss_db = (
                42.6
                + distance_term_db
                + frequency_term_db
                + model_correction_db
            )
            return PropagationResult(
                model_name=self.name,
                distance_m=distance_m,
                path_loss_db=path_loss_db,
                formula_source=self.formula_source,
                intermediate_values={
                    "propagation_condition": "los",
                    "distance_km": distance_km,
                    "distance_term_db": distance_term_db,
                    "frequency_term_db": frequency_term_db,
                    "model_correction_db": model_correction_db,
                },
            )

        if building_height_m <= input_data.mobile_height_m:
            raise ValueError("building_height_m must exceed mobile_height_m for COST231-WI NLOS.")

        fspl_db = (
            32.4
            + 20.0 * math.log10(input_data.frequency_mhz)
            + 20.0 * math.log10(distance_km)
        )
        orientation_correction_db = _street_orientation_correction(
            street_orientation_deg
        )
        rooftop_to_street_db = _rooftop_to_street_loss(
            frequency_mhz=input_data.frequency_mhz,
            street_width_m=street_width_m,
            building_height_m=building_height_m,
            mobile_height_m=input_data.mobile_height_m,
            orientation_correction_db=orientation_correction_db,
        )
        multiscreen_db, multiscreen_values = _multiscreen_loss(
            frequency_mhz=input_data.frequency_mhz,
            distance_m=distance_m,
            building_spacing_m=building_spacing_m,
            building_height_m=building_height_m,
            base_height_m=input_data.base_height_m,
            city_type=city_type,
        )
        additional_loss_db = max(rooftop_to_street_db + multiscreen_db, 0.0)
        path_loss_db = fspl_db + additional_loss_db + model_correction_db

        return PropagationResult(
            model_name=self.name,
            distance_m=distance_m,
            path_loss_db=path_loss_db,
            formula_source=self.formula_source,
            intermediate_values={
                "fspl_db": fspl_db,
                "propagation_condition": "nlos",
                "street_orientation_correction_db": orientation_correction_db,
                "rooftop_to_street_db": rooftop_to_street_db,
                "multiscreen_db": multiscreen_db,
                **multiscreen_values,
                "additional_loss_db": additional_loss_db,
                "model_correction_db": model_correction_db,
            },
        )


class LowBandGroundModel:
    name = "Low-Band Calibrated Ground"
    formula_source = "Close-in reference log-distance engineering model"

    def calculate_path_loss(
        self, input_data: CalculationInput, distance_m: float
    ) -> PropagationResult:
        if distance_m <= 0:
            raise ValueError("distance_m must be greater than 0.")
        if not 300.0 <= input_data.frequency_mhz <= 500.0:
            raise ValueError("Low-band ground frequency must be between 300 MHz and 500 MHz.")

        reference_distance_m = float(input_data.scenario_params["reference_distance_m"])
        path_loss_exponent = float(input_data.scenario_params["path_loss_exponent"])
        model_correction_db = float(
            input_data.scenario_params.get("model_correction_db", 0.0)
        )
        min_distance_m, max_distance_m = model_distance_bounds(input_data)
        if reference_distance_m <= 0.0 or path_loss_exponent <= 0.0:
            raise ValueError("Low-band reference distance and path loss exponent must be positive.")
        if not min_distance_m <= distance_m <= max_distance_m:
            raise ValueError(
                "Low-band ground distance must be within the calibration range."
            )

        reference_path_loss_db = _free_space_path_loss_db(
            input_data.frequency_mhz, reference_distance_m
        )
        distance_term_db = 10.0 * path_loss_exponent * math.log10(
            distance_m / reference_distance_m
        )
        path_loss_db = reference_path_loss_db + distance_term_db + model_correction_db
        return PropagationResult(
            model_name=self.name,
            distance_m=distance_m,
            path_loss_db=path_loss_db,
            formula_source=self.formula_source,
            intermediate_values={
                "reference_distance_m": reference_distance_m,
                "reference_path_loss_db": reference_path_loss_db,
                "path_loss_exponent": path_loss_exponent,
                "distance_term_db": distance_term_db,
                "model_correction_db": model_correction_db,
                "calibration_status": str(
                    input_data.scenario_params.get("calibration_status", "unverified")
                ),
            },
        )


class ViaductModel:
    name = "Ground Model + Viaduct Calibration"
    formula_source = "Selected ground model with traceable viaduct calibration"

    def __init__(self) -> None:
        self._cost_model = Cost231WiModel()
        self._low_band_model = LowBandGroundModel()

    def calculate_path_loss(
        self, input_data: CalculationInput, distance_m: float
    ) -> PropagationResult:
        base_model = (
            self._low_band_model
            if str(input_data.scenario_params.get("ground_model", "low_band"))
            == "low_band"
            else self._cost_model
        )
        base_result = base_model.calculate_path_loss(input_data, distance_m)
        viaduct_correction_db = float(
            input_data.scenario_params.get("viaduct_correction_db", 0.0)
        )
        train_blockage_loss_db = float(
            input_data.scenario_params.get("train_blockage_loss_db", 0.0)
        )
        calibration_offset_db = float(
            input_data.scenario_params.get("calibration_offset_db", 0.0)
        )
        correction_db = (
            viaduct_correction_db
            + train_blockage_loss_db
            + calibration_offset_db
        )
        path_loss_db = base_result.path_loss_db + correction_db

        intermediate_values = dict(base_result.intermediate_values)
        intermediate_values.update(
            {
                "base_model_name": base_result.model_name,
                "viaduct_correction_db": viaduct_correction_db,
                "train_blockage_loss_db": train_blockage_loss_db,
                "calibration_offset_db": calibration_offset_db,
                "total_viaduct_correction_db": correction_db,
                "calibration_status": str(
                    input_data.scenario_params.get("calibration_status", "unverified")
                ),
            }
        )

        return PropagationResult(
            model_name=f"{base_result.model_name} + Viaduct Calibration",
            distance_m=distance_m,
            path_loss_db=path_loss_db,
            formula_source=(
                f"{base_result.formula_source}; traceable viaduct calibration"
            ),
            intermediate_values=intermediate_values,
        )


def _rooftop_to_street_loss(
    *,
    frequency_mhz: float,
    street_width_m: float,
    building_height_m: float,
    mobile_height_m: float,
    orientation_correction_db: float,
) -> float:
    width = max(street_width_m, 1.0)
    height_delta = max(building_height_m - mobile_height_m, 1.0)
    return (
        -16.9
        - 10.0 * math.log10(width)
        + 10.0 * math.log10(frequency_mhz)
        + 20.0 * math.log10(height_delta)
        + orientation_correction_db
    )


def _multiscreen_loss(
    *,
    frequency_mhz: float,
    distance_m: float,
    building_spacing_m: float,
    building_height_m: float,
    base_height_m: float,
    city_type: str,
) -> tuple[float, dict[str, float]]:
    distance_km = max(distance_m / 1000.0, 0.001)
    spacing = max(building_spacing_m, 1.0)
    height_delta = base_height_m - building_height_m
    if height_delta > 0.0:
        base_station_height_loss_db = -18.0 * math.log10(1.0 + height_delta)
        ka = 54.0
        kd = 18.0
    else:
        base_station_height_loss_db = 0.0
        ka = (
            54.0 - 0.8 * height_delta
            if distance_km >= 0.5
            else 54.0 - 0.8 * height_delta * distance_km / 0.5
        )
        kd = 18.0 - 15.0 * height_delta / building_height_m
    frequency_coefficient = 1.5 if city_type == "metropolitan" else 0.7
    kf = -4.0 + frequency_coefficient * ((frequency_mhz / 925.0) - 1.0)
    spacing_loss_db = -9.0 * math.log10(spacing)
    multiscreen_db = (
        base_station_height_loss_db
        + ka
        + kd * math.log10(distance_km)
        + kf * math.log10(frequency_mhz)
        + spacing_loss_db
    )
    return multiscreen_db, {
        "base_station_height_loss_db": base_station_height_loss_db,
        "ka": ka,
        "kd": kd,
        "kf": kf,
        "spacing_loss_db": spacing_loss_db,
    }


def _street_orientation_correction(street_orientation_deg: float) -> float:
    if 0.0 <= street_orientation_deg < 35.0:
        return -10.0 + 0.354 * street_orientation_deg
    if street_orientation_deg < 55.0:
        return 2.5 + 0.075 * (street_orientation_deg - 35.0)
    if street_orientation_deg <= 90.0:
        return 4.0 - 0.114 * (street_orientation_deg - 55.0)
    raise ValueError("street_orientation_deg must be between 0 and 90 degrees.")


def get_model(
    input_data: CalculationInput,
) -> ItuIndoorModel | TunnelModel | Cost231WiModel | LowBandGroundModel | ViaductModel:
    if input_data.scenario_type == "underground":
        return ItuIndoorModel()
    if input_data.scenario_type == "tunnel":
        return TunnelModel()
    if input_data.scenario_type == "ground":
        if str(input_data.scenario_params.get("ground_model", "")) == "low_band":
            return LowBandGroundModel()
        return Cost231WiModel()
    if input_data.scenario_type == "viaduct":
        return ViaductModel()
    raise ValueError(f"Unsupported scenario_type: {input_data.scenario_type}")


def model_distance_bounds(input_data: CalculationInput) -> tuple[float, float]:
    if input_data.scenario_type in {"ground", "viaduct"}:
        ground_model = str(input_data.scenario_params.get("ground_model", ""))
        if ground_model == "cost231_wi":
            return 20.0, 5000.0
        if ground_model == "low_band":
            return (
                float(input_data.scenario_params["calibration_min_distance_m"]),
                float(input_data.scenario_params["calibration_max_distance_m"]),
            )
    return 1.0, 50_000.0
