#!/usr/bin/env python3
"""
Wait until a Gazebo Transport service becomes available.

This script is used by launch files that need to delay follow-up actions until
Gazebo has finished creating a world-level service such as
`/world/<world_name>/create`.

The script does not use ROS services. It queries Gazebo directly with
`gz service -l`, polls until the requested service appears, and exits with:
- `0` when the service becomes available
- `1` when the timeout expires

Launch code can use that exit status to continue with dependent actions or to
shut the launch down with a clear error.
"""

import argparse
import math
import subprocess
import sys
import time


def _positive_finite_float(value: str) -> float:
    """Parse a positive finite number from one command-line value."""
    try:
        parsed_value = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid number: '{value}'.") from exc

    if not math.isfinite(parsed_value) or parsed_value <= 0.0:
        raise argparse.ArgumentTypeError(f"Value must be positive and finite: '{value}'.")

    return parsed_value


def _absolute_service_name(value: str) -> str:
    """Require the absolute service name printed by `gz service -l`."""
    if not value.startswith('/') or not value.removeprefix('/').strip():
        raise argparse.ArgumentTypeError(
            f"Gazebo service name must start with '/' and contain a name: '{value}'."
        )

    return value


def _parse_args() -> argparse.Namespace:
    """Parse the command-line options used to wait for a Gazebo service."""
    parser = argparse.ArgumentParser(description='Wait until a Gazebo service becomes available.')
    parser.add_argument(
        'service_name',
        type=_absolute_service_name,
        help='Absolute Gazebo service name to wait for.',
    )
    parser.add_argument(
        '--timeout',
        type=_positive_finite_float,
        default=60.0,
        help='Maximum time in seconds to wait before failing.',
    )
    parser.add_argument(
        '--poll-period',
        type=_positive_finite_float,
        default=0.25,
        help='Seconds between Gazebo service-list checks.',
    )
    return parser.parse_args()


def _service_exists(service_name: str) -> bool:
    """
    Return whether the requested Gazebo service is currently advertised.

    The `gz service -l` command prints the Gazebo Transport services known at that moment.
    This function requires an exact line match so a shorter service name cannot match a different
    service that merely contains the same text.
    """
    result = subprocess.run(['gz', 'service', '-l'], capture_output=True, text=True, check=False)

    # Treat command failures as a temporary unavailable state.
    # The caller continues polling until the configured timeout expires.
    if result.returncode != 0:
        print(
            f"wait_for_gz_service.py: 'gz service -l' failed with code {result.returncode}",
            file=sys.stderr,
        )
        return False

    return service_name in result.stdout.splitlines()


def main() -> int:
    """
    Wait for the requested service and return its availability as a process exit code.

    The function returns `0` when the service becomes available and `1` when the timeout expires.
    """
    args = _parse_args()
    start = time.monotonic()

    print(f"wait_for_gz_service.py: waiting for Gazebo service '{args.service_name}'", flush=True)

    while True:
        if _service_exists(args.service_name):
            elapsed = time.monotonic() - start
            print(
                f"wait_for_gz_service.py: service '{args.service_name}' became available after "
                f'{elapsed:.2f} s',
                flush=True,
            )
            return 0

        elapsed = time.monotonic() - start

        if elapsed >= args.timeout:
            print(
                f'wait_for_gz_service.py: timed out after {elapsed:.2f} s waiting for '
                f"'{args.service_name}'",
                file=sys.stderr,
                flush=True,
            )
            return 1

        # Sleeping prevents a busy loop while preserving the configured response interval.
        time.sleep(args.poll_period)


if __name__ == '__main__':
    raise SystemExit(main())
