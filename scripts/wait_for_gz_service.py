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
import subprocess
import sys
import time


def _parse_args() -> argparse.Namespace:
    """Parse the command-line options used to wait for a Gazebo service."""
    parser = argparse.ArgumentParser(description='Wait until a Gazebo service becomes available.')
    parser.add_argument('service_name', help='Full Gazebo service name to wait for')
    parser.add_argument('--timeout', type=float, default=60.0, help='Maximum time in seconds to wait before failing')
    parser.add_argument(
        '--poll-period', type=float, default=0.25, help='Polling period in seconds between service list checks'
    )
    return parser.parse_args()


def _service_exists(service_name: str) -> bool:
    """
    Return whether the requested Gazebo service is currently advertised.

    The check is performed with `gz service -l`, which prints the list of
    Gazebo Transport services known at that moment.

    Args:
        service_name: Full Gazebo service name, for example
            `/world/office_environment_1/create`.

    Returns:
        bool: `True` if the service is listed, `False` otherwise.
    """
    result = subprocess.run(['gz', 'service', '-l'], capture_output=True, text=True, check=False)

    # Treat command failures as "service not available yet". The caller keeps
    # polling until the timeout expires.
    if result.returncode != 0:
        print(f"wait_for_gz_service.py: 'gz service -l' failed with code {result.returncode}", file=sys.stderr)
        return False

    return service_name in result.stdout.splitlines()


def main() -> int:
    """Wait for the requested service and return a process exit code.

    Returns:
        int: `0` when the service becomes available, `1` when the timeout
        expires first.
    """
    args = _parse_args()
    start = time.monotonic()

    print(f"wait_for_gz_service.py: waiting for Gazebo service '{args.service_name}'", flush=True)

    while True:
        if _service_exists(args.service_name):
            elapsed = time.monotonic() - start
            print(
                f"wait_for_gz_service.py: service '{args.service_name}' became available after {elapsed:.2f} s",
                flush=True,
            )
            return 0

        elapsed = time.monotonic() - start

        if elapsed >= args.timeout:
            print(
                f"wait_for_gz_service.py: timed out after {elapsed:.2f} s waiting for '{args.service_name}'",
                file=sys.stderr,
                flush=True,
            )
            return 1

        # A short sleep avoids busy-waiting while still reacting quickly once
        # Gazebo advertises the requested service.
        time.sleep(args.poll_period)


if __name__ == '__main__':
    raise SystemExit(main())
