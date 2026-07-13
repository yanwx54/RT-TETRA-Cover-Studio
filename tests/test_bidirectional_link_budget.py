from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rt_tetra_cover_studio.engine import calculate_link_budget
from rt_tetra_cover_studio.models import CalculationInput


def reference_input() -> CalculationInput:
    return CalculationInput(
        frequency_mhz=860.0,
        base_tx_power_w=25.0,
        mobile_tx_power_w=1.0,
        base_antenna_gain_dbi=9.0,
        base_feeder_loss_db=2.0,
        base_other_loss_db=3.0,
        mobile_antenna_gain_dbi=0.0,
        body_loss_db=3.0,
        mobile_receiver_sensitivity_dbm=-103.0,
        base_receiver_sensitivity_dbm=-112.0,
        base_diversity_gain_db=0.0,
        shadow_fading_std_db=8.0,
        edge_coverage_probability_pct=95.0,
        interference_margin_db=2.0,
        penetration_loss_db=10.0,
        base_height_m=5.0,
        mobile_height_m=1.5,
        scenario_type="ground",
        scenario_params={
            "building_height_m": 18.0,
            "building_spacing_m": 40.0,
            "street_width_m": 20.0,
        },
    )


class BidirectionalLinkBudgetTest(unittest.TestCase):
    def test_reference_bidirectional_link_budget(self) -> None:
        result = calculate_link_budget(reference_input())

        self.assertAlmostEqual(result.base_eirp_dbm, 47.98, places=2)
        self.assertAlmostEqual(result.mobile_eirp_dbm, 27.00, places=2)
        self.assertAlmostEqual(result.shadow_fading_margin_db, 13.16, places=2)
        self.assertAlmostEqual(result.required_rx_mobile_dbm, -74.84, places=2)
        self.assertAlmostEqual(result.required_rx_base_dbm, -90.84, places=2)
        self.assertAlmostEqual(result.downlink_mapl_db, 122.82, places=2)
        self.assertAlmostEqual(result.uplink_mapl_db, 117.84, places=2)
        self.assertAlmostEqual(result.max_path_loss_db, 117.84, places=2)
        self.assertEqual(result.limiting_link, "上行")

    def test_power_is_converted_from_watts_to_dbm(self) -> None:
        result = calculate_link_budget(reference_input())

        self.assertAlmostEqual(
            result.base_eirp_dbm, 10.0 * 4.39794 + 9.0 - 2.0 - 3.0, places=6
        )
        self.assertAlmostEqual(result.mobile_eirp_dbm, 30.0 - 3.0)


if __name__ == "__main__":
    unittest.main()
