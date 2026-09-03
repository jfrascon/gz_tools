"""Test validation used by the floor-plan mesh generator."""

import argparse
import importlib.util
import math
from pathlib import Path
from types import ModuleType

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_script() -> ModuleType:
    """Load the maintenance script without executing its command-line entry point."""
    script_path = PACKAGE_ROOT / 'scripts' / 'build_stl_from_png.py'
    spec = importlib.util.spec_from_file_location('build_stl_from_png', script_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('value', ['0.1', '2', '1e-6'])
def test_positive_float_accepts_positive_finite_values(value: str) -> None:
    """Accept positive finite dimensions and resolutions."""
    module = _load_script()

    assert module.positive_float(value) == float(value)


@pytest.mark.parametrize('value', ['0', '-1', 'nan', 'inf', '-inf', 'invalid'])
def test_positive_float_rejects_invalid_values(value: str) -> None:
    """Reject values that cannot represent a usable physical dimension."""
    module = _load_script()

    with pytest.raises(argparse.ArgumentTypeError):
        module.positive_float(value)


def test_positive_float_never_returns_a_non_finite_value() -> None:
    """Protect downstream geometry operations from non-finite input."""
    module = _load_script()

    assert math.isfinite(module.positive_float('10.5'))
