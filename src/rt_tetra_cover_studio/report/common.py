from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
import struct
from typing import Any
import zlib


@dataclass
class ReportChartImage:
    title: str
    image: BytesIO


def project_info_rows(template: dict[str, Any], report_data: dict[str, Any]) -> list[tuple[str, str]]:
    rows = [(str(key), str(value)) for key, value in template.get("project_info", {}).items()]
    input_data = report_data["input"]
    summary = report_data["summary"]
    rows.extend(
        [
            ("计算场景", str(input_data["scenario_type"])),
            ("传播模型", str(summary["model_name"])),
            ("报告生成时间", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ]
    )
    return rows


def build_curve_chart_images(charts: dict[str, Any]) -> list[ReportChartImage]:
    path_loss_curve = charts["path_loss_curve"]
    rssi_curve = charts["rssi_curve"]
    boundary = charts["coverage_boundary"]
    distances = [point["distance_m"] for point in path_loss_curve]
    return [
        ReportChartImage(
            "Path Loss - Distance",
            _build_chart_image(
                x_values=distances,
                y_values=[point["path_loss_db"] for point in path_loss_curve],
                boundary_x=boundary["distance_m"],
                boundary_y=boundary["path_loss_db"],
            ),
        ),
        ReportChartImage(
            "RSSI - Distance",
            _build_chart_image(
                x_values=distances,
                y_values=[point["rssi_dbm"] for point in rssi_curve],
                boundary_x=boundary["distance_m"],
                boundary_y=boundary["rssi_dbm"],
            ),
        ),
    ]


def _build_chart_image(
    *,
    x_values: list[float],
    y_values: list[float],
    boundary_x: float,
    boundary_y: float,
) -> BytesIO:
    width = 900
    height = 450
    margin_left = 76
    margin_right = 28
    margin_top = 30
    margin_bottom = 58
    pixels = [[(255, 255, 255) for _ in range(width)] for _ in range(height)]

    x_min = min(x_values)
    x_max = max(x_values)
    if x_min == x_max:
        x_min -= 1
        x_max += 1
    y_min = min(y_values)
    y_max = max(y_values)
    if y_min == y_max:
        y_min -= 1
        y_max += 1
    y_padding = (y_max - y_min) * 0.08
    y_min -= y_padding
    y_max += y_padding

    plot_left = margin_left
    plot_right = width - margin_right
    plot_top = margin_top
    plot_bottom = height - margin_bottom

    def map_x(value: float) -> int:
        return int(plot_left + (value - x_min) / (x_max - x_min) * (plot_right - plot_left))

    def map_y(value: float) -> int:
        return int(plot_bottom - (value - y_min) / (y_max - y_min) * (plot_bottom - plot_top))

    for index in range(6):
        x = int(plot_left + index * (plot_right - plot_left) / 5)
        _draw_line(pixels, x, plot_top, x, plot_bottom, (226, 232, 238))
        y = int(plot_top + index * (plot_bottom - plot_top) / 5)
        _draw_line(pixels, plot_left, y, plot_right, y, (226, 232, 238))

    _draw_line(pixels, plot_left, plot_top, plot_left, plot_bottom, (45, 55, 65), thickness=2)
    _draw_line(pixels, plot_left, plot_bottom, plot_right, plot_bottom, (45, 55, 65), thickness=2)
    _draw_line(
        pixels,
        map_x(boundary_x),
        plot_top,
        map_x(boundary_x),
        plot_bottom,
        (198, 40, 40),
        thickness=2,
    )

    points = [(map_x(x), map_y(y)) for x, y in zip(x_values, y_values)]
    for start, end in zip(points, points[1:]):
        _draw_line(pixels, start[0], start[1], end[0], end[1], (23, 105, 170), thickness=3)
    _draw_marker(pixels, map_x(boundary_x), map_y(boundary_y), (198, 40, 40))

    image = BytesIO()
    image.write(_encode_png(pixels))
    image.seek(0)
    return image


def _draw_line(
    pixels: list[list[tuple[int, int, int]]],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
    thickness: int = 1,
) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    while True:
        _paint(pixels, x0, y0, color, thickness)
        if x0 == x1 and y0 == y1:
            break
        next_error = 2 * error
        if next_error >= dy:
            error += dy
            x0 += sx
        if next_error <= dx:
            error += dx
            y0 += sy


def _draw_marker(
    pixels: list[list[tuple[int, int, int]]], x: int, y: int, color: tuple[int, int, int]
) -> None:
    for offset_y in range(-5, 6):
        for offset_x in range(-5, 6):
            if offset_x * offset_x + offset_y * offset_y <= 25:
                _paint(pixels, x + offset_x, y + offset_y, color)


def _paint(
    pixels: list[list[tuple[int, int, int]]],
    x: int,
    y: int,
    color: tuple[int, int, int],
    thickness: int = 1,
) -> None:
    radius = max(0, thickness // 2)
    for offset_y in range(-radius, radius + 1):
        for offset_x in range(-radius, radius + 1):
            target_y = y + offset_y
            target_x = x + offset_x
            if 0 <= target_y < len(pixels) and 0 <= target_x < len(pixels[0]):
                pixels[target_y][target_x] = color


def _encode_png(pixels: list[list[tuple[int, int, int]]]) -> bytes:
    height = len(pixels)
    width = len(pixels[0])
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for red, green, blue in row:
            raw.extend((red, green, blue))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(bytes(raw), level=9))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack("!I", len(data))
        + chunk_type
        + data
        + struct.pack("!I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )
