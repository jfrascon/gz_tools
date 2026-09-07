"""Test SDF world-name extraction."""

import xml.etree.ElementTree as ET

import pytest

from ros_gz_tools.helpers import get_world_name
from ros_gz_tools.helpers import get_world_name_from_string


def test_get_world_name_reads_a_file(tmp_path) -> None:
    """Read the direct world name from an SDF file."""
    world_file = tmp_path / 'world.sdf'
    world_file.write_text('<sdf version="1.9"><world name="factory"/></sdf>', encoding='utf-8')

    assert get_world_name(world_file) == 'factory'


def test_get_world_name_from_string_reads_inline_sdf() -> None:
    """Read the direct world name from inline SDF XML."""
    assert get_world_name_from_string('<sdf version="1.9"><world name="warehouse"/></sdf>') == (
        'warehouse'
    )


@pytest.mark.parametrize(
    'world_sdf',
    [
        '<sdf version="1.9"/>',
        '<sdf version="1.9"><world/></sdf>',
        '<sdf version="1.9"><world name=""/></sdf>',
        '<sdf version="1.9"><world name="   "/></sdf>',
    ],
)
def test_get_world_name_rejects_missing_world_metadata(world_sdf: str) -> None:
    """Reject SDF that cannot provide a non-empty world name."""
    with pytest.raises(ValueError):
        get_world_name_from_string(world_sdf)


def test_get_world_name_preserves_xml_parse_errors() -> None:
    """Expose malformed SDF as the standard ElementTree parse error."""
    with pytest.raises(ET.ParseError):
        get_world_name_from_string('<sdf><world name="broken"></sdf>')
