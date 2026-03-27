import os
from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory
from catkin_pkg.package import PACKAGE_MANIFEST_FILENAME, InvalidPackage, parse_package
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.utilities.type_utils import normalize_typed_substitution, perform_typed_substitution
from launch_ros.actions import Node
from ros2pkg.api import get_package_names

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity

# This launch starts one Gazebo world and one dedicated `/clock` bridge.
#
# The Gazebo process itself is still started by
# `ros_gz_sim/launch/gz_sim.launch.py`, but this file owns the logic around
# that process:
# - it prepares `GZ_SIM_RESOURCE_PATH`
# - it prepares `GZ_SIM_SYSTEM_PLUGIN_PATH`
# - it forwards Gazebo CLI options such as `initial_sim_time`
# - it writes the bridge YAML consumed by `ros_gz_bridge/bridge_node`
#
# This file intentionally does not delegate everything to the higher-level
# `GzServer` and `RosGzBridge` actions.
#
# Reason 1:
# `ros_gz_sim.launch.py` is convenient for basic usage, but it does not expose
# every Gazebo option that this package wants to pass through. One concrete
# example is `initial_sim_time`, which exists in the lower-level Gazebo server
# action but is not surfaced by that launch file.
# Reference:
# https://github.com/gazebosim/ros_gz/blob/ros2/ros_gz_sim/launch/gz_sim.launch.py.in
#
# Reason 2:
# launching Gazebo through the `GzServer` action is not ideal here. That action
# does not expose a `namespace` argument, so it is not a good fit when Gazebo-
# related nodes must interact with already-namespaced containers or with launch
# flows that make namespace handling explicit.
#
# Reason 3:
# this package wants the world launcher to own only the world process and the
# `/clock` bridge. Sensor bridges and robot spawning are intentionally handled
# elsewhere, so the responsibilities stay separated.
#
# About the bridge implementation:
# `ros_gz_bridge` can be configured in several ways, for example with
# `RosGzBridge`, with `parameter_bridge`, or with a YAML configuration passed to
# `bridge_node`. This file uses `bridge_node` plus a generated YAML file because
# it keeps the `/clock` bridge configuration explicit and isolated from the rest
# of the launch flow.
# References:
# https://github.com/gazebosim/ros_gz/tree/ros2/ros_gz_bridge
#   #example-7-configuring-the-bridge-via-python-launch-file
# https://github.com/gazebosim/ros_gz/blob/ros2/ros_gz_bridge/src/parameter_bridge.cpp
#
# When this file is included from another launch file, pass `namespace:=...`
# directly to this file instead of relying on `PushRosNamespace`.
# `PushRosNamespace` is still awkward around some composable-node workflows in
# `launch_ros`, especially when the target container already lives in a
# namespace and the included launch file must resolve names explicitly.
#
# Reference for that namespace limitation:
# https://github.com/ros2/launch_ros/issues/428
# Discussion about a possible fix:
# https://github.com/ros2/launch_ros/pull/429


def generate_launch_description():
    ldes: list[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(name='namespace', default_value='', description='Namespace'),
        DeclareLaunchArgument(
            'world_file',
            default_value='empty.sdf',
            description='World file name or absolute .sdf path to load in Gazebo Sim',
        ),
        DeclareLaunchArgument(
            'extra_resource_paths',
            default_value='',
            description=(
                'Additional Gazebo resource directories to append to GZ_SIM_RESOURCE_PATH. '
                'Use a comma-separated list to provide more than one directory. '
                'This argument is intended for resources that do not belong to a ROS package '
                'in the current workspace, such as a world stored on the user desktop together '
                'with its meshes, models, or media files. If a world references '
                '`model://my_model`, pass the parent directory that contains the '
                '`my_model/` folder, not the `my_model/` folder itself.'
            ),
        ),
        DeclareLaunchArgument(
            'gui',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Run Gazebo Sim with GUI. If False, run in headless mode (default: False)',
        ),
        DeclareLaunchArgument('gui_config_file', default_value='', description='Gazebo GUI configuration file to load'),
        DeclareLaunchArgument(
            'autostart',
            default_value='True',
            choices=['True', 'true', 'False', 'false'],
            description='Run simulation on start (default: True)',
        ),
        DeclareLaunchArgument(
            'initial_sim_time', default_value='0.0', description='Initial simulation time in seconds (default: 0.0)'
        ),
        DeclareLaunchArgument(
            'verbosity',
            default_value='1',
            choices=['0', '1', '2', '3', '4'],
            description='Verbosity level for Gazebo Sim (default: 1, range: 0-4)',
        ),
        DeclareLaunchArgument(
            'update_rate',
            default_value='',
            description='Update rate in Hertz. Leave empty to keep Gazebo default behavior',
        ),
        DeclareLaunchArgument(
            'respawn_bridge',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Whether to respawn the bridge node if it dies (default: False)',
        ),
        DeclareLaunchArgument(
            'log_level_bridge',
            default_value='info',
            choices=['debug', 'info', 'warn', 'error'],
            description='Log level for the bridge node (default: info)',
        ),
        OpaqueFunction(function=set_environment_variables),
        OpaqueFunction(function=spawn_world),
    ]

    return LaunchDescription(ldes)


def spawn_world(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """
    Build the Gazebo launch actions and the ROS-to-Gazebo clock bridge.
    """
    # The externally visible behavior of this function is:
    # - start Gazebo with the requested world and CLI options
    # - start one bridge node that publishes `/clock` into ROS
    #
    # Gazebo itself still comes from `ros_gz_sim/launch/gz_sim.launch.py`,
    # which ultimately launches the `gz sim` executable. That is useful here
    # because the `gz sim` CLI exposes options such as verbosity, autostart,
    # update rate, and initial simulation time in a direct and predictable way.
    gz_args: list[str] = []

    gui = perform_typed_substitution(ctx, normalize_typed_substitution(LaunchConfiguration('gui'), bool), bool)
    gui_config_file = LaunchConfiguration('gui_config_file').perform(ctx)

    if not gui:
        gz_args.append('-s')
    elif gui_config_file:
        gz_args.extend([' --gui-config ', gui_config_file])
    else:
        gz_args.extend(
            [' --gui-config ', os.path.join(get_package_share_directory('ros_gz_tools'), 'config', 'gui.config')]
        )

    autostart = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('autostart'), bool), bool
    )

    if autostart:
        gz_args.append(' -r')

    # The launch argument stays empty by default so the command line only
    # includes `-z` when the caller explicitly requests an update rate.
    update_rate = LaunchConfiguration('update_rate').perform(ctx)

    if update_rate:
        gz_args.extend([' -z', update_rate])

    world_file = LaunchConfiguration('world_file').perform(ctx)
    world_file_path = Path(world_file)
    world_file_stem = world_file_path.stem
    world_file_ext = world_file_path.suffix

    if world_file_ext != '.sdf':
        raise ValueError(f"The world file '{world_file}' does not have the required extension '.sdf'")

    gz_args.extend(
        [
            ' --initial-sim-time ',
            LaunchConfiguration('initial_sim_time').perform(ctx),
            ' -v',
            LaunchConfiguration('verbosity').perform(ctx),
            ' ',
            world_file,
        ]
    )

    ros_home = Path(os.environ.get('ROS_HOME', '~/.ros')).expanduser()
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    bridge_file = f'{world_file_stem}_bridge.yaml'

    if namespace not in ('', '/'):
        bridge_file = namespace.strip('/').replace('/', '_') + '_' + bridge_file

    abs_bridge_file = os.path.join(ros_home, bridge_file)
    abs_bridge_path = Path(abs_bridge_file)

    abs_bridge_path.parent.mkdir(parents=True, exist_ok=True)

    bridge_channel = [
        {
            'ros_topic_name': '/clock',
            'gz_topic_name': '/clock',
            'ros_type_name': 'rosgraph_msgs/msg/Clock',
            'gz_type_name': 'gz.msgs.Clock',
            'direction': 'GZ_TO_ROS',
            'qos_profile': 'CLOCK',
            'lazy': False,
        }
    ]

    with abs_bridge_path.open('w', encoding='utf-8') as f:
        yaml.safe_dump(
            bridge_channel, stream=f, sort_keys=False, default_flow_style=False, allow_unicode=True, width=120
        )

    return [
        # `gz_sim.launch.py` ultimately launches the Gazebo executable, not a
        # ROS node. ROS-specific concepts such as namespace or `use_sim_time`
        # are therefore only meaningful for the ROS nodes started by this file.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments={'gz_args': gz_args}.items(),
        ),
        Node(
            package='ros_gz_bridge',
            executable='bridge_node',
            name='bridge_clock',
            namespace=namespace,
            output='screen',
            respawn=LaunchConfiguration('respawn_bridge'),
            respawn_delay=2.0,
            parameters=[
                {
                    'subscription_heartbeat': 1000,  # Default used by ros_gz_bridge.
                    'config_file': abs_bridge_file,
                    'expand_gz_topic_names': False,  # Keep `/clock` unchanged on both sides.
                    'override_timestamps_with_wall_time': False,  # `/clock` must publish sim time.
                }
            ],
            arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level_bridge')],
        ),
    ]


def set_environment_variables(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """
    Populate Gazebo resource and plugin paths before Gazebo starts.
    """

    def remove_duplicates(paths: list[str]) -> list[str]:
        """
        Normalize a path list and preserve the first occurrence of each entry.
        """
        return list(dict.fromkeys(os.path.normpath(os.path.expanduser(p)) for p in paths if p))

    # `gazebo_model_path` and `gazebo_media_path` exports are appended to
    # `GZ_SIM_RESOURCE_PATH`. `plugin_path` exports are appended to
    # `GZ_SIM_SYSTEM_PLUGIN_PATH`.
    model_paths, plugin_paths = get_gazebo_paths()

    ament_prefix_path = os.getenv('AMENT_PREFIX_PATH', default='')
    resource_paths: list[str] = []

    if ament_prefix_path:
        # Gazebo often needs the `share` directory of ROS packages to resolve
        # meshes referenced from robot descriptions and SDF files.
        for raw_path in ament_prefix_path.split(os.pathsep):
            path = raw_path.strip()
            if path:
                resource_paths.append(os.path.join(path, 'share'))

    extra_resource_paths = LaunchConfiguration('extra_resource_paths').perform(ctx).strip()

    if extra_resource_paths:
        resource_paths.extend(path.strip() for path in extra_resource_paths.split(',') if path.strip())

    all_resource_paths = remove_duplicates(
        resource_paths
        + model_paths.split(os.pathsep)
        + os.environ.get('GZ_SIM_RESOURCE_PATH', default='').split(os.pathsep)
    )

    gz_sim_resource_path = os.pathsep.join(all_resource_paths)

    all_plugin_paths = remove_duplicates(
        plugin_paths.split(os.pathsep)
        + os.environ.get('GZ_SIM_SYSTEM_PLUGIN_PATH', default='').split(os.pathsep)
        + os.environ.get('LD_LIBRARY_PATH', default='').split(os.pathsep)
    )

    gz_sim_system_plugin_path = os.pathsep.join(all_plugin_paths)

    return [
        SetEnvironmentVariable(name='GZ_SIM_SYSTEM_PLUGIN_PATH', value=gz_sim_system_plugin_path),
        SetEnvironmentVariable(name='GZ_SIM_RESOURCE_PATH', value=gz_sim_resource_path),
        LogInfo(msg=['GZ_SIM_SYSTEM_PLUGIN_PATH: ', gz_sim_system_plugin_path]),
        LogInfo(msg=['GZ_SIM_RESOURCE_PATH: ', gz_sim_resource_path]),
    ]


def get_gazebo_paths() -> tuple[str, str]:
    """
    Collect Gazebo resource and plugin exports from installed ROS packages.

    This mirrors the resource discovery strategy used by `ros_gz_sim` so this
    package resolves models and plugins the same way Gazebo-related ROS tools do.
    """
    gazebo_model_path = []
    gazebo_plugin_path = []
    gazebo_media_path = []

    for package_name in get_package_names():
        package_share_path = get_package_share_directory(package_name)
        package_file_path = os.path.join(package_share_path, PACKAGE_MANIFEST_FILENAME)
        if os.path.isfile(package_file_path):
            try:
                package = parse_package(package_file_path)
            except InvalidPackage:
                continue
            for export in package.exports:
                if export.tagname == 'gazebo_ros':
                    if 'gazebo_model_path' in export.attributes:
                        xml_path = export.attributes['gazebo_model_path']
                        xml_path = xml_path.replace('${prefix}', package_share_path)
                        gazebo_model_path.append(xml_path)
                    if 'plugin_path' in export.attributes:
                        xml_path = export.attributes['plugin_path']
                        xml_path = xml_path.replace('${prefix}', package_share_path)
                        gazebo_plugin_path.append(xml_path)
                    if 'gazebo_media_path' in export.attributes:
                        xml_path = export.attributes['gazebo_media_path']
                        xml_path = xml_path.replace('${prefix}', package_share_path)
                        gazebo_media_path.append(xml_path)

    gazebo_model_path = os.pathsep.join(gazebo_model_path + gazebo_media_path)
    gazebo_plugin_path = os.pathsep.join(gazebo_plugin_path)

    return gazebo_model_path, gazebo_plugin_path
