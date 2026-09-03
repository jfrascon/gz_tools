#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
import math
import os
import subprocess
import sys
import tempfile


def positive_float(value: str) -> float:
    """Parse a positive finite float from one command-line value."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f'Invalid float value: {value}') from exc

    if not math.isfinite(parsed) or parsed <= 0.0:
        raise argparse.ArgumentTypeError(f'Value must be positive and finite: {value}')

    return parsed


def generate_default_output_path() -> str:
    """Generate a default STL output path in /tmp using mktemp-like naming."""
    date_prefix = datetime.now(timezone.utc).strftime('%Y%m%d')
    template = f'/tmp/{date_prefix}-XXXXXX.stl'

    try:
        result = subprocess.run(['mktemp', template], check=True, capture_output=True, text=True)
        output_path = result.stdout.strip()
        if output_path:
            return output_path
    except (OSError, subprocess.CalledProcessError):
        pass

    # Fall back to Python's tempfile helpers when `mktemp` is not available.
    fd, output_path = tempfile.mkstemp(dir='/tmp', prefix=f'{date_prefix}-', suffix='.stl')
    os.close(fd)
    return output_path


def parse_args() -> tuple[str, str, float, float]:
    """Build runtime configuration for STL generation from CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            'Generate a 3D STL wall model from a 2D floor plan PNG. '
            'Input image convention: black = obstacles, white = free space.'
        )
    )

    parser.add_argument(
        'image_path', type=str, help='Path to the input PNG image where black represents obstacles.'
    )

    parser.add_argument(
        'resolution', type=positive_float, help='Positive finite resolution in meters per pixel.'
    )

    parser.add_argument(
        'height', type=positive_float, help='Positive finite wall height in meters.'
    )

    parser.add_argument(
        '--output',
        dest='output_path',
        type=str,
        default=None,
        help='Output STL path. If omitted, an output path is auto-generated in /tmp.',
    )

    args = parser.parse_args()
    output_path = args.output_path

    if output_path is None:
        output_path = generate_default_output_path()
        print(f'No output path provided. Using generated path: {output_path}')

    return args.image_path, output_path, args.resolution, args.height


def generate_stl(image_path, output_path, resolution, height):
    """
    Generate an STL wall mesh from a floor-plan PNG image.

    The input image must use black pixels for obstacles and white pixels for free space.
    `resolution` scales image pixels to meters, and `height` sets the wall extrusion in meters.
    """
    try:
        import cv2
        from shapely.geometry import Polygon
        import trimesh
    except ModuleNotFoundError as exc:
        print(
            (
                f"Error: Missing Python dependency '{exc.name}'. "
                'Install these packages: opencv-python, numpy, scipy, trimesh, shapely, and '
                'mapbox-earcut.'
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    print(f'Loading image: {image_path}...')
    # Read the image in grayscale so thresholding does not depend on color data.
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    if img is None:
        print(f"Error: Could not load image from '{image_path}'.", file=sys.stderr)
        sys.exit(1)

    # Invert the binary image so black walls become foreground polygons.
    _, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    mesh_list = []

    for i, contour in enumerate(contours):
        if len(contour) >= 3:
            # Use the original contour points.
            # Additional simplification can create self-intersections and invalid polygons.
            points_2d = contour.reshape(-1, 2) * resolution
            poly = Polygon(points_2d)

            # Extrude only valid polygons that enclose a non-zero area.
            if poly.is_valid and poly.area > 0:
                try:
                    mesh = trimesh.creation.extrude_polygon(poly, height=height)
                    mesh_list.append(mesh)
                except Exception as exc:
                    print(
                        f'Warning: Polygon {i} skipped due to geometry error: {exc}',
                        file=sys.stderr,
                    )

    if mesh_list:
        # Downstream Gazebo worlds expect one mesh for the complete environment.
        final_mesh = trimesh.util.concatenate(mesh_list)
        final_mesh.export(output_path)
        print(f'Success! STL saved as: {output_path}')
    else:
        print('Error: No valid 3D walls could be generated.', file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Parse CLI arguments and run the STL generation workflow."""
    image_path, output_path, resolution, height = parse_args()
    generate_stl(image_path, output_path, resolution, height)


if __name__ == '__main__':
    main()
