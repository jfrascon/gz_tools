"""Test the Gazebo service-wait helper."""

import argparse
import importlib.util
from pathlib import Path
import subprocess
from types import ModuleType

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_script() -> ModuleType:
    """Load the installed-script source without running its command-line entry point."""
    script_path = PACKAGE_ROOT / 'scripts' / 'wait_for_gz_service.py'
    spec = importlib.util.spec_from_file_location('wait_for_gz_service', script_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('value', ['0.01', '1', '60.5'])
def test_positive_finite_float_accepts_valid_periods(value: str) -> None:
    """Accept positive finite timeout and polling values."""
    module = _load_script()

    assert module._positive_finite_float(value) == float(value)


@pytest.mark.parametrize('value', ['0', '-1', 'nan', 'inf', '-inf', 'invalid'])
def test_positive_finite_float_rejects_invalid_periods(value: str) -> None:
    """Reject values that could break or disable the timeout loop."""
    module = _load_script()

    with pytest.raises(argparse.ArgumentTypeError):
        module._positive_finite_float(value)


@pytest.mark.parametrize('value', ['', 'create', '/', '/   '])
def test_absolute_service_name_rejects_unusable_names(value: str) -> None:
    """Reject names that cannot match the absolute names printed by Gazebo."""
    module = _load_script()

    with pytest.raises(argparse.ArgumentTypeError):
        module._absolute_service_name(value)


def test_service_exists_requires_an_exact_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not confuse one service with a longer service that shares its text."""
    module = _load_script()
    completed = subprocess.CompletedProcess(
        args=['gz', 'service', '-l'],
        returncode=0,
        stdout='/world/factory/create_extra\n/world/factory/remove\n',
        stderr='',
    )
    monkeypatch.setattr(module.subprocess, 'run', lambda *args, **kwargs: completed)

    assert not module._service_exists('/world/factory/create')
    assert module._service_exists('/world/factory/remove')


def test_service_exists_treats_command_failure_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allow the polling loop to retry after a temporary Gazebo command failure."""
    module = _load_script()
    completed = subprocess.CompletedProcess(
        args=['gz', 'service', '-l'], returncode=1, stdout='', stderr='not ready'
    )
    monkeypatch.setattr(module.subprocess, 'run', lambda *args, **kwargs: completed)

    assert not module._service_exists('/world/factory/create')
