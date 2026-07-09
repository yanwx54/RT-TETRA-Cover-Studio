from __future__ import annotations

from typing import Any


def extract_chart_series(charts: dict[str, Any]) -> dict[str, Any]:
    path_loss_curve = charts["path_loss_curve"]
    rssi_curve = charts["rssi_curve"]
    boundary = charts["coverage_boundary"]

    return {
        "distance_m": [point["distance_m"] for point in path_loss_curve],
        "path_loss_db": [point["path_loss_db"] for point in path_loss_curve],
        "rssi_dbm": [point["rssi_dbm"] for point in rssi_curve],
        "boundary_distance_m": boundary["distance_m"],
        "boundary_path_loss_db": boundary["path_loss_db"],
        "boundary_rssi_dbm": boundary["rssi_dbm"],
    }
