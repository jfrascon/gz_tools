import os
from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory
from catkin_pkg.package import PACKAGE_MANIFEST_FILENAME, InvalidPackage, parse_package
from launch_ros.actions import Node
from ros2pkg.api import get_package_names

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
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

# ======================================================================================================================
# NOTE: To include the nodes used in this launch file in a namespace, do not use the action PushRosNamespace in
# conjunction with this launch file in a parent launch file, just pass the namespace as a parameter to this launch file.

# If you inclue this python launch file in parent launch, using the action PushRosNamespace along with this launch
# file, when 'use_composition' is set to True, the composable nodes to load into a container do no get the namespace
# defined in the PushRosNamespace action automatically, when the namespace is different from pure '/', so they do not
# find the container (namespaced), and they are not loaded.
# There is PR to solve that issue, in which composable nodes get the namespace automatically, but this PR has not been
# merged yet (2025-08-06) since it is no clear the approach the ROS community wants to follow, regarding inhering the
# namespace for composable nodes.
# Issue: https://github.com/ros2/launch_ros/issues/428
# PR: https://github.com/ros2/launch_ros/pull/429 -> There is kind of a discussion here about the approach to follow.

# So, for the time being, to load the composable nodes in the namespace of a container, you have to pass the namespace
# as a parameter to this launch file.
# ======================================================================================================================

# If you are familiar with the package 'ros_gz_sim', you might know that there is a launch file in that package called
# 'ros_gz_sim.launch.py', which is convenient to launch the Gazebo server and a bridge to transfer topics between ROS2
# and Gazebo.
# Internally that launch file uses the actions GzServer and RosGzBridge to launch the Gazebo server and the bridge.
# There is a parameter that the action GzServer defines, 'initial_sim_time', that is not defined in the launch file
# 'ros_gz_sim.launch.py', so if you use that launch file, by including it in this launch file, you will not be able to
# set the initial simulation time and forward it to the GZServer action, in the rare case you need to do that.
# So, you might be wondering: is it really necessary to set the initial simulation time in a project?
# The answer is: no, it is not necessary ... MOST OF THE TIME, but imagine that rare case where you need to set the
# initial simulation time to a specific value, like 10 seconds, so that the simulation starts at that time, instead of
# starting at 0 seconds. If you stick to the inclusion of the launch file 'ros_gz_sim.launch.py', you will not be able
# to set that parameter.

# So, next obvious step was to include the actions GzServer and RosGzBridge directly in this launch file and use them,
# the same way the launch file 'ros_gz_sim.launch.py' does, but know we can pass the 'initial_sim_time' parameter to the
# GzServer action.
# Well ..., not really, using GzServer action is not a good idea. The action does not include a parameter 'namespace',
# so in the case you want to use composition and load the gzserver into an already existing container, you will not be
# able to specify the fully qualified name using the namespace + container name.
# So, if we are not going to use the GzServer actions, we can omit using the action RosGzBridge, as well, and
# manage the composable nodes directly in this launch file w/o the syntactic sugar of these actions, and in fact this
# is not difficult at all the code is very understandable.

# For more information about composition you can read an introduction in:
# https://gazebosim.org/docs/harmonic/ros2_overview/#composition

# For a tutorial in composition you can read:
# https://docs.ros.org/en/jazzy/How-To-Guides/Launching-composable-nodes.html#launch-file-examples

# I also leave here some notes on briges:

# When running a bridge you might find different ways:
# 1. Using a RosGzBridge action.
# 2. Using the node 'parameter_bridge' from the package 'ros_gz_bridge', like shown in the example 7 of the README
# file found in the package 'ros_gz_bridge':
# https://github.com/gazebosim/ros_gz/tree/ros2/ros_gz_bridge#example-7-configuring-the-bridge-via-python-launch-file
# Node(
#     package="ros_gz_bridge",
#     executable="parameter_bridge",
#     parameters=[
#         {"bridge_names": ["clock_bridge"]},
#         {"bridges.clock_bridge.ros_topic_name": "/clock"},
#         {"bridges.clock_bridge.gz_topic_name": "/clock"},
#         {"bridges.clock_bridge.ros_type_name": "rosgraph_msgs/msg/Clock"},
#         {"bridges.clock_bridge.gz_type_name": "gz.msgs.Clock"},
#         {"bridges.clock_bridge.direction": "GZ_TO_ROS"},
#         {"bridges.clock_bridge.lazy": "False"},
#         {"bridges.clock_bridge.qos_profile": "CLOCK"},
#     ],
# )
# 3. Using the node 'parameter_bridge' from the package 'ros_gz_bridge', but using the arguments instead of
# parameters.
# Node(
#         package='ros_gz_bridge',
#         executable='parameter_bridge',
#         name='clock_gz_bridge',
#         output='screen'4188202149517441,
#         # Descriptions at:
#         # Reference: https://github.com/gazebosim/ros_gz/tree/ros2/ros_gz_bridge#readme
#         # Referente: https://github.com/gazebosim/ros_gz/blob/ros2/ros_gz_bridge/src/parameter_bridge.cpp#L30
#         arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
#     )
# 4. Using the executable directly, like we do in this launch file.
# Method 3 is less preferred, since it can't specify all the options, like the other methods, just by using the format
# '<topic_name>@<ros_type_name><direction><gz_type_name>'.


def generate_launch_description():
    # (L)aunch (d)escription (e)ntitie(s)
    ldes: list[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(name='namespace', default_value='', description='Namespace'),
        DeclareLaunchArgument(
            'world_file', default_value='empty.sdf', description='World file w/o parent path (default: empty.sdf)'
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
            description='Run simulation on start. Available if use_composition is False (default: True)',
        ),
        DeclareLaunchArgument(
            'initial_sim_time', default_value='0.0', description='Initial simulation time in seconds (default: 0.0)'
        ),
        DeclareLaunchArgument(
            'verbosity',
            default_value='1',
            choices=['0', '1', '2', '3', '4'],
            description=(
                'Verbosity level for Gazebo Sim. Available if use_composition is False (default: 1, range: 0-4)'
            ),
        ),
        DeclareLaunchArgument(
            'update_rate',
            default_value='',
            description='Update rate in Hertz. Available if use_composition is False (default: ?)',
        ),
        DeclareLaunchArgument(
            'respawn_rosgz_bridge',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Whether to respawn the rosgz_bridge_node if it dies (default: False)',
        ),
        DeclareLaunchArgument(
            'log_level_rosgz_bridge',
            default_value='info',
            choices=['debug', 'info', 'warn', 'error'],
            description='Log level for the rosgz_bridge_node (default: info)',
        ),
        OpaqueFunction(function=set_environment_variables),
        OpaqueFunction(function=spawn_world),
    ]

    return LaunchDescription(ldes)


# ----------------------------------------------------------------------------------------------------------------------


# Opaque functions.


def spawn_world(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """
    Create the Gazebo server and the clock bridge standard nodes.
    """
    # Standard node configuration
    # When no using composition, it makes more sense to use directy the 'gz sim' command,  the one you would use
    # from a terminal, instead of using the Node 'gzserver', since the 'gzserver' node does no include some interesting
    # parameters that we can pass to the 'gz sim' command, like:
    # - The verbosity level, from 0 to 4. The gzserver node that launches the Gazebo server sets the verbosity level to
    #   a fix value of 4 (too verbose).
    # - Autostart flag, to control whether the simulation starts automatically or not.
    # - The update rate in Hertz.
    # There are many more parameters that can be passed to the 'gz sim' command, but these are what I find
    # more useful for a regular basis use.
    # To check the parameters that can be passed to the 'gz sim' command, you can run in a terminal:
    # gz sim --help
    gz_args: list[str] = []

    # If the user wants to run Gazebo Sim in headless mode, we do not launch the GUI.
    # If the user also wants Gazebo's GUI, we launch the GUI with the configuration file specified by the user, or
    # with the default configuration file 'gz_tools/config/gui.config' if the user does not specify a
    # configuration file.
    gui = perform_typed_substitution(ctx, normalize_typed_substitution(LaunchConfiguration('gui'), bool), bool)

    gui_config_file = LaunchConfiguration('gui_config_file').perform(ctx)

    if not gui:  # Check if Gazebo Sim must be run in headless mode.
        gz_args.append('-s')
    # In the following two branches the gui is enabled, so we configure the gui.
    elif gui_config_file:
        gz_args.extend([' --gui-config ', gui_config_file])
    else:
        gz_args.extend(
            [' --gui-config ', os.path.join(get_package_share_directory('gz_tools'), 'config', 'gui.config')]
        )

    autostart = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('autostart'), bool), bool
    )

    if autostart:
        gz_args.append(' -r')

    # Since we do not know the default value of the 'update_rate' for Gazebo, we let the default value for the
    # 'update_rate' parameter be an empty string, so that the user can set it to a value or not.
    # If we knew the default value for the 'update_rate', we could have set it to that value, and then no matter if the
    # user sets a value or not, the 'update_rate' parameter would be set to a valid value, and we could use the
    # statement
    # perform_typed_substitution(ctx, normalize_typed_substitution(LaunchConfiguration('update_rate'), float), float).
    update_rate = LaunchConfiguration('update_rate').perform(ctx)

    # If the 'update_rate' is not empty, we append it to the gz_args list.
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

    ros_home = Path(os.environ.get('ROS_HOME', os.path.expanduser('~/.ros')))
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    suffix = f'{world_file_stem}_rosgz_bridge.yaml'
    rosgz_bridge_file = suffix if namespace in ('', '/') else namespace.strip('/').replace('/', '_') + '_' + suffix
    abs_rosgz_bridge_file = os.path.join(ros_home, rosgz_bridge_file)
    abs_rosgz_bridge_path = Path(abs_rosgz_bridge_file)

    # Make sure the parent directory exists.
    abs_rosgz_bridge_path.parent.mkdir(parents=True, exist_ok=True)

    rosgz_bridge_channel = [
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

    with abs_rosgz_bridge_path.open('w', encoding='utf-8') as f:
        yaml.safe_dump(
            rosgz_bridge_channel, stream=f, sort_keys=False, default_flow_style=False, allow_unicode=True, width=120
        )

    return [
        # The Node(...) action is left here for reference.
        # Node(
        #     package='ros_gz_sim',
        #     executable='gzserver',
        #     name='gz_server',
        #     namespace=namespace,
        #     output='screen',
        #     parameters=[gz_server_parameters],
        # ),
        # The following include does not run a ROS node, it launches an executable 'ruby $(which gz) sim ...', (see
        # ros_gz_sim/launch/gz_sim.launch.py), so the 'use_sim_time' and namespace parameters are not understood by
        # this executable.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments={'gz_args': gz_args}.items(),
        ),
        Node(
            package='ros_gz_bridge',
            executable='bridge_node',
            name='rosgz_bridge_clock',
            namespace=namespace,
            output='screen',
            respawn=LaunchConfiguration('respawn_rosgz_bridge'),
            respawn_delay=2.0,
            parameters=[
                {
                    'subscription_heartbeat': 1000,  # default value in 'ros_gz_bridge.cpp''
                    'config_file': abs_rosgz_bridge_file,
                    'expand_gz_topic_names': False,  # We want to use exact topic names.
                    'override_timestamps_with_wall_time': False,  # Not needed for /clock
                }
            ],
            arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level_rosgz_bridge')],
        ),
    ]


def set_environment_variables(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """
    Set the environment variables for the Gazebo Sim paths.
    """

    def remove_duplicates(paths: list[str]) -> list[str]:
        """
        Remove duplicates from a list of paths and normalize them.
        """
        return list(dict.fromkeys(os.path.normpath(os.path.expanduser(p)) for p in paths if p))

    # model_paths will be added into the environment variable GZ_SIM_RESOURCE_PATH.
    # plugin_pahts will be added into the environment variable GZ_SIM_PLUGIN_PATH.
    model_paths, plugin_paths = get_gazebo_paths()

    # print(f'Model paths = {model_paths}')
    # print(f'Plugin paths = {plugin_paths}')

    # To spawn a world in Gazebo Sim, you just pass proper value in the parameter 'world_file', like 'empty.sdf' (in
    # default path for Gazebo), or 'sky.sdf' (in default path for Gazebo), or 'maze.sdf' (in gz_tools/worlds).

    # We need to set the GZ_SIM_RESOURCE_PATH environment variable properly to find the meshes used in the
    # robot_description topics.
    # If you want Gazebo to find the meshes of your robot, you need to add to the GZ_SIM_RESOURCE_PATH environment
    # variable the paths listed in the environment variable AMENT_PREFIX_PATH + 'share'.

    ament_prefix_path = os.getenv('AMENT_PREFIX_PATH', default='')

    resource_paths: list[str] = []

    if ament_prefix_path:
        resource_paths.extend([os.path.join(p, 'share') for p in ament_prefix_path.split(os.pathsep)])
        # print(f'Resource paths = {os.pathsep.join(resource_paths)}')

    # print(f'GZ_SIM_RESOURCE_PATH: {os.environ.get("GZ_SIM_RESOURCE_PATH", default="")}')

    # All paths, without duplicates.
    all_resource_paths = remove_duplicates(
        resource_paths
        + model_paths.split(os.pathsep)
        + os.environ.get('GZ_SIM_RESOURCE_PATH', default='').split(os.pathsep)
    )

    gz_sim_resource_path = os.pathsep.join(all_resource_paths)
    # print(f'gz_sim_resource_path: {gz_sim_resource_path}')

    all_plugin_paths = remove_duplicates(
        plugin_paths.split(os.pathsep)
        + os.environ.get('GZ_SIM_SYSTEM_PLUGIN_PATH', default='').split(os.pathsep)
        + os.environ.get('LD_LIBRARY_PATH', default='').split(os.pathsep)
    )

    gz_sim_system_plugin_path = os.pathsep.join(all_plugin_paths)
    # print(f'gz_sim_system_plugin_path: {gz_sim_system_plugin_path}')

    return [
        SetEnvironmentVariable(name='GZ_SIM_SYSTEM_PLUGIN_PATH', value=gz_sim_system_plugin_path),
        SetEnvironmentVariable(name='GZ_SIM_RESOURCE_PATH', value=gz_sim_resource_path),
        LogInfo(msg=['GZ_SIM_SYSTEM_PLUGIN_PATH: ', gz_sim_system_plugin_path]),
        LogInfo(msg=['GZ_SIM_RESOURCE_PATH: ', gz_sim_resource_path]),
    ]


# Non-opaque functions

# Code extracted from the function 'get_paths' in the class 'GazeboRosPaths', in the file
# https://github.com/gazebosim/ros_gz/tree/ros2/ros_gz_sim/ros_gz_sim/actions/gzserver.py
# Same function and class can be found in the file
# https://github.com/gazebosim/ros_gz/blob/ros2/ros_gz_sim/launch/gz_sim.launch.py.in


def get_gazebo_paths() -> tuple[str, str]:
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
