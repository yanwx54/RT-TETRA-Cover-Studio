"""Core package for RT-TETRA Cover Studio."""

from .engine import calculate_coverage
from .models import CalculationInput, CalculationResult

__all__ = ["CalculationInput", "CalculationResult", "calculate_coverage"]
