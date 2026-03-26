#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def positive_float(value):
    """Parse a CLI value as a positive float."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f'Invalid float value: {value}') from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError(f'Value must be > 0: {value}')

    return parsed


def generate_default_output_path():
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


def parse_args():
    """Build runtime configuration for STL generation from CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            'Generate a 3D STL wall model from a 2D floor plan PNG. '
            'Input image convention: black = obstacles, white = free space.'
        )
    )

    parser.add_argument('image_path', type=str, help='Path to the input PNG image (black=obstacles, white=free space)')

    parser.add_argument('resolution', type=positive_float, help='Resolution in meters per pixel (float > 0)')

    parser.add_argument('height', type=positive_float, help='Height of the walls in meters (float > 0)')

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
    """Generate an STL wall mesh from a floor-plan PNG image.

    The input image must use black pixels for obstacles and white pixels for
    free space.

    Args:
        image_path: Path to the input PNG image.
        output_path: Path where the output STL file will be written.
        resolution: Meters per pixel used to scale contour coordinates.
        height: Extrusion height in meters for each detected obstacle.
    """
    try:
        import cv2
        import trimesh
        from shapely.geometry import Polygon
    except ModuleNotFoundError as exc:
        print(
            (
                f"Error: Missing Python dependency '{exc.name}'. "
                'Install required packages: opencv-python numpy scipy trimesh shapely mapbox-earcut.'
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
            # Use the original contour points. Additional simplification can
            # create self-intersections and invalid polygons.
            points_2d = contour.reshape(-1, 2) * resolution
            poly = Polygon(points_2d)

            # Only extrude polygons that Shapely considers valid and that
            # actually enclose a non-zero area.
            if poly.is_valid and poly.area > 0:
                try:
                    mesh = trimesh.creation.extrude_polygon(poly, height=height)
                    mesh_list.append(mesh)
                except Exception as e:
                    print(f'Warning: Polygon {i} skipped due to geometry error: {e}', file=sys.stderr)

    if mesh_list:
        # Export a single STL because downstream Gazebo usage expects one mesh
        # file for the whole environment.
        final_mesh = trimesh.util.concatenate(mesh_list)
        final_mesh.export(output_path)
        print(f'Success! STL saved as: {output_path}')
    else:
        print('Error: No valid 3D walls could be generated.', file=sys.stderr)
        sys.exit(1)


def main():
    """Parse CLI arguments and run the STL generation workflow."""
    image_path, output_path, resolution, height = parse_args()
    generate_stl(image_path, output_path, resolution, height)


if __name__ == '__main__':
    main()
