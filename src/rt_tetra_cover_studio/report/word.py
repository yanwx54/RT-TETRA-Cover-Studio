from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE_PATH = PROJECT_DIR / "config" / "report_template.json"


def export_word_report(
    report_data: dict[str, Any],
    output_path: str | Path,
    template_path: str | Path = DEFAULT_TEMPLATE_PATH,
) -> Path:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - exercised only without dependency.
        raise RuntimeError("python-docx is required to export Word reports.") from exc

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    template = _load_template(template_path)

    document = Document()
    document.add_heading(template["title"], level=0)
    document.add_paragraph(template["subtitle"])

    _add_summary(document, report_data["summary"])
    _add_input_table(document, report_data["input"])
    _add_link_budget(document, report_data["details"]["link_budget"])
    _add_iteration_summary(document, report_data["details"]["iteration_steps"])
    _add_curve_summary(document, report_data["charts"], template["curve_sample_points"])
    _add_warnings(document, report_data["summary"].get("warnings", []))

    document.save(path)
    return path


def _load_template(template_path: str | Path) -> dict[str, Any]:
    with Path(template_path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _add_summary(document: Any, summary: dict[str, Any]) -> None:
    document.add_heading("核心结论", level=1)
    rows = [
        ("传播模型", summary["model_name"]),
        ("最大覆盖距离", f"{summary['coverage_distance_m']:.1f} m"),
        ("覆盖等级", summary["coverage_level"]),
        ("EIRP", f"{summary['eirp_dbm']:.2f} dBm"),
        ("最大允许路径损耗", f"{summary['max_path_loss_db']:.2f} dB"),
        ("覆盖边界 RSSI", f"{summary['boundary_rssi_dbm']:.2f} dBm"),
    ]
    _add_key_value_table(document, rows)


def _add_input_table(document: Any, input_data: dict[str, Any]) -> None:
    document.add_heading("输入参数", level=1)
    rows = []
    for key, value in input_data.items():
        if key == "scenario_params":
            for param_key, param_value in value.items():
                rows.append((f"scenario_params.{param_key}", param_value))
        else:
            rows.append((key, value))
    _add_key_value_table(document, rows)


def _add_link_budget(document: Any, link_budget: dict[str, Any]) -> None:
    document.add_heading("链路预算", level=1)
    document.add_paragraph(f"EIRP：{link_budget['eirp_dbm']:.2f} dBm")
    document.add_paragraph(f"最大允许路径损耗：{link_budget['max_path_loss_db']:.2f} dB")
    table = document.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    _set_cells(table.rows[0].cells, ["步骤", "公式", "代入", "结果"])
    for step in link_budget["steps"]:
        cells = table.add_row().cells
        _set_cells(
            cells,
            [
                step["name"],
                step["formula"],
                step["substitution"],
                f"{step['result']:.2f} {step['unit']}",
            ],
        )


def _add_iteration_summary(document: Any, iteration_steps: list[dict[str, Any]]) -> None:
    document.add_heading("覆盖距离求解", level=1)
    document.add_paragraph(f"迭代记录数量：{len(iteration_steps)}")
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    _set_cells(table.rows[0].cells, ["迭代", "距离(m)", "Path Loss(dB)"])
    for step in iteration_steps[:10]:
        cells = table.add_row().cells
        _set_cells(
            cells,
            [
                str(step["iteration"]),
                f"{step['distance_m']:.1f}",
                f"{step['path_loss_db']:.2f}",
            ],
        )


def _add_curve_summary(
    document: Any, charts: dict[str, Any], sample_points: int
) -> None:
    document.add_heading("曲线数据摘要", level=1)
    boundary = charts["coverage_boundary"]
    document.add_paragraph(
        "覆盖边界："
        f"{boundary['distance_m']:.1f} m，"
        f"Path Loss {boundary['path_loss_db']:.2f} dB，"
        f"RSSI {boundary['rssi_dbm']:.2f} dBm"
    )

    path_loss_curve = charts["path_loss_curve"]
    rssi_curve = charts["rssi_curve"]
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    _set_cells(table.rows[0].cells, ["距离(m)", "Path Loss(dB)", "RSSI(dBm)"])
    for path_point, rssi_point in list(zip(path_loss_curve, rssi_curve))[:sample_points]:
        cells = table.add_row().cells
        _set_cells(
            cells,
            [
                f"{path_point['distance_m']:.1f}",
                f"{path_point['path_loss_db']:.2f}",
                f"{rssi_point['rssi_dbm']:.2f}",
            ],
        )


def _add_warnings(document: Any, warnings: list[str]) -> None:
    document.add_heading("计算提示", level=1)
    if warnings:
        for warning in warnings:
            document.add_paragraph(warning, style="List Bullet")
    else:
        document.add_paragraph("无告警")


def _add_key_value_table(document: Any, rows: list[tuple[str, Any]]) -> None:
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    _set_cells(table.rows[0].cells, ["项目", "值"])
    for key, value in rows:
        cells = table.add_row().cells
        _set_cells(cells, [str(key), str(value)])


def _set_cells(cells: Any, values: list[str]) -> None:
    for cell, value in zip(cells, values):
        cell.text = value
