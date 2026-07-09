"""Core package for RT-TETRA Cover Studio."""

from .engine import calculate_coverage
from .io import calculation_input_from_dict, load_example_case
from .models import CalculationInput, CalculationResult

__all__ = [
    "CalculationInput",
    "CalculationResult",
    "calculate_coverage",
    "calculation_input_from_dict",
    "load_example_case",
]
