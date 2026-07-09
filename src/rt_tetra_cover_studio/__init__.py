"""Core package for RT-TETRA Cover Studio."""

from .engine import calculate_coverage
from .io import (
    calculation_input_from_dict,
    calculation_input_to_dict,
    calculation_result_to_dict,
    load_example_case,
    save_calculation_result,
)
from .models import CalculationInput, CalculationResult
from .report import export_pdf_report, export_word_report

__all__ = [
    "CalculationInput",
    "CalculationResult",
    "calculate_coverage",
    "calculation_input_from_dict",
    "calculation_input_to_dict",
    "calculation_result_to_dict",
    "load_example_case",
    "save_calculation_result",
    "export_pdf_report",
    "export_word_report",
]
