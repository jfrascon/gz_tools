"""Utilities for reading Gazebo world metadata from SDF documents."""

from pathlib import Path
import xml.etree.ElementTree as ET


def get_world_name(world_file: str | Path) -> str:
    """
    Return the Gazebo world name defined in one SDF file.

    The function raises `ValueError` when the SDF document has no direct `<world>` element or the
    element does not define a non-empty `name` attribute.
    """
    return _get_world_name_from_root(ET.parse(world_file).getroot(), str(world_file))


def get_world_name_from_string(world_sdf_string: str) -> str:
    """Return the Gazebo world name defined in one SDF string."""
    return _get_world_name_from_root(ET.fromstring(world_sdf_string), 'world_sdf_string')


def _get_world_name_from_root(root: ET.Element, source: str) -> str:
    """Return the world name from one parsed SDF XML root."""
    world = root.find('world')

    if world is None:
        raise ValueError(f"World source '{source}' does not contain a <world> element")

    world_name = world.get('name')

    if not world_name or not world_name.strip():
        raise ValueError(f"World source '{source}' does not define a name in its <world> element")

    return world_name
