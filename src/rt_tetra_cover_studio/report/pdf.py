from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import build_curve_chart_images, project_info_rows
from ..paths import resource_path


DEFAULT_TEMPLATE_PATH = resource_path("config", "report_template.json")
FONT_NAME = "STSong-Light"


def export_pdf_report(
    report_data: dict[str, Any],
    output_path: str | Path,
    template_path: str | Path = DEFAULT_TEMPLATE_PATH,
) -> Path:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    except ImportError as exc:  # pragma: no cover - exercised only without dependency.
        raise RuntimeError("ReportLab is required to export PDF reports.") from exc

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    template = _load_template(template_path)

    pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ChineseTitle",
            parent=styles["Title"],
            fontName=FONT_NAME,
            fontSize=18,
            leading=24,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ChineseHeading",
            parent=styles["Heading2"],
            fontName=FONT_NAME,
            fontSize=13,
            leading=18,
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ChineseBody",
            parent=styles["BodyText"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=13,
        )
    )

    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    story: list[Any] = [
        _paragraph(template["title"], styles["ChineseTitle"]),
        _paragraph(template["subtitle"], styles["ChineseBody"]),
        Spacer(1, 8),
    ]
    _add_project_info(story, styles, project_info_rows(template, report_data), colors)
    _add_summary(story, styles, report_data["summary"], colors)
    _add_input_table(story, styles, report_data["input"], colors)
    _add_calculation_sections(
        story, styles, report_data["details"]["calculation_sections"], colors
    )
    _add_iteration_summary(story, styles, report_data["details"]["iteration_steps"], colors)
    _add_curve_summary(story, styles, report_data["charts"], template["curve_sample_points"], colors)
    _add_curve_images(story, styles, report_data["charts"])
    _add_warnings(story, styles, report_data["summary"].get("warnings", []), colors)

    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_header_footer(canvas, doc, template),
        onLaterPages=lambda canvas, doc: _draw_header_footer(canvas, doc, template),
    )
    return path


def _load_template(template_path: str | Path) -> dict[str, Any]:
    with Path(template_path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _paragraph(text: str, style: Any) -> Any:
    from reportlab.platypus import Paragraph

    return Paragraph(text, style)


def _draw_header_footer(canvas: Any, document: Any, template: dict[str, Any]) -> None:
    from reportlab.lib.units import mm

    width, height = document.pagesize
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.drawString(document.leftMargin, height - 10 * mm, template["title"])
    canvas.drawRightString(
        width - document.rightMargin,
        10 * mm,
        f"{template.get('footer', '')} | 第 {document.page} 页",
    )
    canvas.restoreState()


def _add_project_info(
    story: list[Any], styles: Any, rows: list[tuple[str, str]], colors: Any
) -> None:
    story.append(_paragraph("工程信息", styles["ChineseHeading"]))
    story.append(_key_value_table(rows, colors))


def _add_summary(story: list[Any], styles: Any, summary: dict[str, Any], colors: Any) -> None:
    story.append(_paragraph("核心结论", styles["ChineseHeading"]))
    rows = [
        ("传播模型", summary["model_name"]),
        ("最大覆盖距离", f"{summary['coverage_distance_m']:.1f} m"),
        ("受限链路", summary["limiting_link"]),
        ("基站 EIRP", f"{summary['base_eirp_dbm']:.2f} dBm"),
        ("手台 EIRP", f"{summary['mobile_eirp_dbm']:.2f} dBm"),
        ("下行 MAPL", f"{summary['downlink_mapl_db']:.2f} dB"),
        ("上行 MAPL", f"{summary['uplink_mapl_db']:.2f} dB"),
        ("系统 MAPL", f"{summary['max_path_loss_db']:.2f} dB"),
        ("下行边界 RSSI", f"{summary['boundary_rssi_dbm']:.2f} dBm"),
    ]
    story.append(_key_value_table(rows, colors))


def _add_input_table(story: list[Any], styles: Any, input_data: dict[str, Any], colors: Any) -> None:
    story.append(_paragraph("输入参数", styles["ChineseHeading"]))
    rows = []
    for key, value in input_data.items():
        if key == "scenario_params":
            for param_key, param_value in value.items():
                rows.append((f"scenario_params.{param_key}", param_value))
        else:
            rows.append((key, value))
    story.append(_key_value_table(rows, colors))


def _add_calculation_sections(
    story: list[Any], styles: Any, sections: list[dict[str, Any]], colors: Any
) -> None:
    story.append(_paragraph("详细计算过程", styles["ChineseHeading"]))
    for section in sections:
        story.append(
            _paragraph(
                f"{section['number']} {section['title']}", styles["ChineseHeading"]
            )
        )
        story.append(_paragraph(section["description"], styles["ChineseBody"]))
        rows = [["项目", "内容"]]
        for detail in section["details"]:
            rows.extend(
                [
                    [detail["name"], ""],
                    ["公式", detail["formula"]],
                    ["代入", detail["substitution"]],
                    ["结果", detail["result"]],
                ]
            )
        story.append(_table(rows, colors, [90, 330]))


def _add_iteration_summary(
    story: list[Any], styles: Any, iteration_steps: list[dict[str, Any]], colors: Any
) -> None:
    story.append(_paragraph("覆盖距离求解", styles["ChineseHeading"]))
    story.append(_paragraph(f"迭代记录数量：{len(iteration_steps)}", styles["ChineseBody"]))
    rows = [["迭代", "距离(m)", "Path Loss(dB)"]]
    for step in iteration_steps[:10]:
        rows.append(
            [
                str(step["iteration"]),
                f"{step['distance_m']:.1f}",
                f"{step['path_loss_db']:.2f}",
            ]
        )
    story.append(_table(rows, colors, [48, 80, 90]))


def _add_curve_summary(
    story: list[Any],
    styles: Any,
    charts: dict[str, Any],
    sample_points: int,
    colors: Any,
) -> None:
    story.append(_paragraph("曲线数据摘要", styles["ChineseHeading"]))
    boundary = charts["coverage_boundary"]
    story.append(
        _paragraph(
            "覆盖边界："
            f"{boundary['distance_m']:.1f} m，"
            f"Path Loss {boundary['path_loss_db']:.2f} dB，"
            f"RSSI {boundary['rssi_dbm']:.2f} dBm",
            styles["ChineseBody"],
        )
    )
    rows = [["距离(m)", "Path Loss(dB)", "RSSI(dBm)"]]
    for path_point, rssi_point in list(zip(charts["path_loss_curve"], charts["rssi_curve"]))[
        :sample_points
    ]:
        rows.append(
            [
                f"{path_point['distance_m']:.1f}",
                f"{path_point['path_loss_db']:.2f}",
                f"{rssi_point['rssi_dbm']:.2f}",
            ]
        )
    story.append(_table(rows, colors, [80, 90, 90]))


def _add_curve_images(story: list[Any], styles: Any, charts: dict[str, Any]) -> None:
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Spacer

    story.append(_paragraph("覆盖曲线图", styles["ChineseHeading"]))
    for chart in build_curve_chart_images(charts):
        chart.image.seek(0)
        story.append(_paragraph(chart.title, styles["ChineseBody"]))
        story.append(Image(chart.image, width=160 * mm, height=80 * mm))
        story.append(Spacer(1, 6))


def _add_warnings(story: list[Any], styles: Any, warnings: list[str], colors: Any) -> None:
    story.append(_paragraph("计算提示", styles["ChineseHeading"]))
    rows = [["提示"]]
    rows.extend([[warning] for warning in warnings] if warnings else [["无告警"]])
    story.append(_table(rows, colors, [420]))


def _key_value_table(rows: list[tuple[str, Any]], colors: Any) -> Any:
    return _table([["项目", "值"], *[[str(key), str(value)] for key, value in rows]], colors, [150, 260])


def _table(rows: list[list[str]], colors: Any, column_widths: list[int]) -> Any:
    from reportlab.platypus import Table, TableStyle

    table = Table(rows, colWidths=column_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2d3d")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b9c2cc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table
