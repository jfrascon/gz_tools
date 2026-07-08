"""
Launch one Gazebo Sim world and its ROS-Gazebo bridge.

This launch file starts a Gazebo server from an SDF world file, starts the bridge
configured by a YAML bridge file, and can optionally start the Gazebo GUI as a
separate client process. Static project obstacles should normally live directly
in the SDF world file. Dynamic entities can be spawned by a separate tool.

This launch file is inspired in the file
`/opt/ros/jazzy/share/ros_gz_sim/launch/ros_gz_sim.launch.py`
"""

from pathlib import Path

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, TextSubstitution
from launch.utilities.type_utils import normalize_typed_substitution, perform_typed_substitution
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.parameters_type import ParametersDict
from launch_ros.substitutions import FindPackageShare
from ros_gz_bridge.actions import RosGzBridge
from ros_gz_sim.actions import GzServer
from ros_gz_tools.helpers import get_world_name, get_world_name_from_string


def generate_launch_description() -> LaunchDescription:
    """
    Declare the launch arguments consumed by the generic world bringup.

    Returns:
        LaunchDescription: The launch description with the world bringup action.
    """
    return LaunchDescription(
        [
            DeclareLaunchArgument(name='namespace', default_value='', description='Top-level namespace of the bridge'),
            DeclareLaunchArgument(
                'use_composition',
                default_value='False',
                choices=['True', 'true', 'False', 'false'],
                description='Use composed bringup if True',
            ),
            DeclareLaunchArgument(
                'create_own_container',
                default_value='False',
                choices=['True', 'true', 'False', 'false'],
                description='Whether we should start a ROS container when using composition.',
            ),
            DeclareLaunchArgument(
                'container_name',
                default_value='ros_gz_container',
                description='Name of container that nodes will load in if use composition',
            ),
            DeclareLaunchArgument('world_sdf_file', default_value='', description='Path to the SDF world file'),
            DeclareLaunchArgument('world_sdf_string', default_value='', description='SDF world string'),
            DeclareLaunchArgument('initial_sim_time', default_value='0.0', description='The initial simulation time'),
            DeclareLaunchArgument(
                'verbosity_level',
                default_value='4',
                choices=['0', '1', '2', '3', '4'],
                description='The verbosity level of the Gazebo server (0=FATAL, 4=DEBUG)',
            ),
            DeclareLaunchArgument(
                'use_gz_gui',
                default_value='True',
                choices=['True', 'true', 'False', 'false'],
                description='Launch Gazebo Sim GUI client. If False, Gazebo Sim runs in headless mode',
            ),
            DeclareLaunchArgument(
                'gz_gui_config_file', default_value='', description='Gazebo Sim GUI client configuration file'
            ),
            DeclareLaunchArgument(
                'world_bridge_file',
                default_value='',
                description='YAML file used to configure ros_gz_bridge for the simulation world',
            ),
            DeclareLaunchArgument('bridge_name', default_value='', description='Name of the bridge'),
            DeclareLaunchArgument(
                'bridge_subscription_heartbeat',
                default_value='1000',
                description='Milliseconds between bridge subscription heartbeat checks',
            ),
            DeclareLaunchArgument(
                'bridge_expand_gz_topic_names',
                default_value='True',
                choices=['True', 'true', 'False', 'false'],
                description='Expand Gazebo topic names when bridging topics',
            ),
            DeclareLaunchArgument(
                'bridge_override_timestamps_with_wall_time',
                default_value='False',
                choices=['True', 'true', 'False', 'false'],
                description='Replace bridged message timestamps with wall time',
            ),
            DeclareLaunchArgument(
                'bridge_override_frame_id',
                default_value='',
                description='Frame id override applied by ros_gz_bridge when supported',
            ),
            DeclareLaunchArgument(
                'bridge_use_respawn',
                default_value='False',
                choices=['True', 'true', 'False', 'false'],
                description='Whether to respawn the bridge if it crashes. Applied when composition is disabled.',
            ),
            DeclareLaunchArgument(
                'bridge_log_level',
                default_value='info',
                choices=['debug', 'info', 'warn', 'error', 'fatal'],
                description='Bridge log level',
            ),
            OpaqueFunction(function=_spawn_world),
        ]
    )


def _spawn_world(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """
    Build the actions that start Gazebo, the world bridge, and the optional GUI.

    Args:
        ctx: Launch context used to resolve the launch arguments.

    Returns:
        list[LaunchDescriptionEntity]: Actions that launch the world server,
        bridge, and optional GUI client.
    """
    world_sdf_file = LaunchConfiguration('world_sdf_file').perform(ctx)
    world_sdf_string = LaunchConfiguration('world_sdf_string').perform(ctx)

    # Exactly one world source must be set. bool(...) turns each string into "is present":
    # False means the string is empty and True means the user provided a value. If both
    # booleans are equal, either both sources are missing or both sources were provided.
    if bool(world_sdf_file) == bool(world_sdf_string):
        raise ValueError("Exactly one of launch arguments 'world_sdf_file' or 'world_sdf_string' must be provided")

    if world_sdf_file and not Path(world_sdf_file).is_file():
        raise FileNotFoundError(f"World SDF file '{world_sdf_file}' not found")

    world_name = get_world_name(world_sdf_file) if world_sdf_file else get_world_name_from_string(world_sdf_string)

    world_bridge_file = LaunchConfiguration('world_bridge_file').perform(ctx)

    if not world_bridge_file:
        raise ValueError("Launch argument 'world_bridge_file' must be provided")

    if not Path(world_bridge_file).is_file():
        raise FileNotFoundError(f"World bridge file '{world_bridge_file}' not found")

    bridge_name = LaunchConfiguration('bridge_name').perform(ctx)
    world_bridge_name = bridge_name or f'{world_name}_ros_gz_bridge'

    extra_bridge_params: ParametersDict = {
        (TextSubstitution(text='subscription_heartbeat'),): ParameterValue(
            LaunchConfiguration('bridge_subscription_heartbeat'), value_type=int
        ),
        (TextSubstitution(text='expand_gz_topic_names'),): ParameterValue(
            LaunchConfiguration('bridge_expand_gz_topic_names'), value_type=bool
        ),
        (TextSubstitution(text='override_timestamps_with_wall_time'),): ParameterValue(
            LaunchConfiguration('bridge_override_timestamps_with_wall_time'), value_type=bool
        ),
        (TextSubstitution(text='override_frame_id'),): ParameterValue(
            LaunchConfiguration('bridge_override_frame_id'), value_type=str
        ),
    }

    launch_entities: list[LaunchDescriptionEntity] = [
        LogInfo(msg=f'World file: {world_sdf_file}'),
        LogInfo(msg=f'Bridge file: {world_bridge_file}'),
        LogInfo(msg=f'Bridge name: {world_bridge_name}'),
        LogInfo(msg=f'World name: {world_name}'),
        LogInfo(msg=f'Launch GUI: {LaunchConfiguration("use_gz_gui").perform(ctx).strip()}'),
        GzServer(
            world_sdf_file=LaunchConfiguration('world_sdf_file'),
            world_sdf_string=LaunchConfiguration('world_sdf_string'),
            container_name=LaunchConfiguration('container_name'),
            create_own_container=LaunchConfiguration('create_own_container'),
            use_composition=LaunchConfiguration('use_composition'),
            initial_sim_time=LaunchConfiguration('initial_sim_time'),
            verbosity_level=LaunchConfiguration('verbosity_level'),
        ),
        RosGzBridge(
            bridge_name=world_bridge_name,
            config_file=world_bridge_file,
            container_name=LaunchConfiguration('container_name'),
            create_own_container=False,
            namespace=LaunchConfiguration('namespace'),
            use_composition=LaunchConfiguration('use_composition'),
            use_respawn=LaunchConfiguration('bridge_use_respawn'),
            log_level=LaunchConfiguration('bridge_log_level'),
            bridge_params='',
            extra_bridge_params=extra_bridge_params,
        ),
    ]

    launch_gui = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('use_gz_gui'), bool), bool
    )

    if launch_gui:
        launch_entities.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([FindPackageShare('ros_gz_tools'), 'launch', 'spawn_gui.launch.py'])
                ),
                launch_arguments={'gz_gui_config_file': LaunchConfiguration('gz_gui_config_file')}.items(),
            )
        )

    return launch_entities
