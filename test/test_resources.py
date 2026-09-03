"""Test package-owned Gazebo resources and their installation."""

import os
from pathlib import Path
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MODELS_ROOT = PACKAGE_ROOT / 'models'
OWNED_MODELS = {path.name for path in MODELS_ROOT.iterdir() if (path / 'model.sdf').is_file()}


@pytest.mark.parametrize('model_name', sorted(OWNED_MODELS))
def test_model_metadata_references_an_existing_sdf(model_name: str) -> None:
    """Keep each Gazebo model directory self-contained and loadable."""
    model_directory = MODELS_ROOT / model_name
    metadata_root = ET.parse(model_directory / 'model.config').getroot()
    sdf_files = [(element.text or '').strip() for element in metadata_root.findall('sdf')]

    assert metadata_root.tag == 'model'
    assert sdf_files
    assert all((model_directory / sdf_file).is_file() for sdf_file in sdf_files)


@pytest.mark.parametrize('model_name', sorted(OWNED_MODELS))
def test_model_sdf_uses_its_directory_name(model_name: str) -> None:
    """Keep model:// identifiers aligned with their installed directory names."""
    sdf_root = ET.parse(MODELS_ROOT / model_name / 'model.sdf').getroot()
    model = sdf_root.find('model')

    assert sdf_root.tag == 'sdf'
    assert model is not None
    assert model.get('name') == model_name


@pytest.mark.parametrize('world_file', sorted((PACKAGE_ROOT / 'worlds').glob('*.sdf')))
def test_world_sdf_has_one_named_world(world_file: Path) -> None:
    """Require every installed world file to expose a world name to the launch helper."""
    root = ET.parse(world_file).getroot()
    worlds = root.findall('world')

    assert root.tag == 'sdf'
    assert len(worlds) == 1
    assert worlds[0].get('name')


@pytest.mark.parametrize(
    'sdf_file',
    sorted(MODELS_ROOT.glob('*/model.sdf')) + sorted((PACKAGE_ROOT / 'worlds').glob('*.sdf')),
)
def test_package_resource_uris_exist(sdf_file: Path) -> None:
    """Prevent package:// and owned model:// references from pointing to missing files."""
    root = ET.parse(sdf_file).getroot()

    for uri_element in root.iter('uri'):
        uri = (uri_element.text or '').strip()
        if uri.startswith('package://ros_gz_tools/'):
            resource = PACKAGE_ROOT / uri.removeprefix('package://ros_gz_tools/')
            assert resource.exists(), f'{sdf_file}: {uri}'
        elif uri.startswith('model://'):
            model_path = uri.removeprefix('model://')
            model_name, separator, relative_path = model_path.partition('/')
            if model_name in OWNED_MODELS and separator:
                assert (MODELS_ROOT / model_name / relative_path).exists(), f'{sdf_file}: {uri}'


def test_gui_configuration_is_a_well_formed_plugin_fragment() -> None:
    """Validate the Gazebo GUI file as a list of plugin elements rather than one XML document."""
    gui_fragment = (PACKAGE_ROOT / 'config' / 'gui.config').read_text(encoding='utf-8')
    gui_fragment = gui_fragment.removeprefix('<?xml version="1.0"?>').lstrip()

    root = ET.fromstring(f'<gui>{gui_fragment}</gui>')

    assert root.findall('plugin')


def test_runtime_resources_are_installed_and_exported() -> None:
    """Verify resource installation and the Gazebo search paths created by the package hook."""
    share_directory = Path(get_package_share_directory('ros_gz_tools'))
    install_prefix = share_directory.parents[1]

    assert (share_directory / 'launch' / 'spawn_world.launch.py').is_file()
    assert (share_directory / 'config' / 'gui.config').is_file()
    assert (share_directory / 'models' / 'warehouse' / 'model.sdf').is_file()
    assert (share_directory / 'worlds' / 'warehouse.sdf').is_file()
    assert (share_directory / 'README.md').is_file()
    assert (share_directory / 'LICENSE').is_file()
    assert (install_prefix / 'lib' / 'ros_gz_tools' / 'wait_for_gz_service.py').is_file()

    resource_paths = os.environ.get('GZ_SIM_RESOURCE_PATH', '').split(os.pathsep)
    assert str(share_directory.parent) in resource_paths
    assert str(share_directory / 'models') in resource_paths
