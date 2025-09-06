import os

from ament_index_python.packages import get_package_share_directory
from catkin_pkg.package import PACKAGE_MANIFEST_FILENAME, InvalidPackage, parse_package
from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity, Substitution
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    SetEnvironmentVariable,
    SetLaunchConfiguration,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.utilities.type_utils import normalize_typed_substitution, perform_typed_substitution
from launch_ros.actions import LoadComposableNodes, Node
from launch_ros.descriptions import ComposableNode
from ros2pkg.api import get_package_names

# ======================================================================================================================
# NOTE: If you inclue this python launch file in parent launch, using the action PushRosNamespace along with this
# launch file, when 'use_composition' is set to True, the composable nodes to load into a container do no get the
# namespace automatically, when the namespace is different from pure '/', so they do not find the container
# (namespaced), and they are not loaded.
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
# There is a parameter that the action GZServer defines, 'initial_sim_time', that is not defined in the launch file
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
# Well, no, using GzServer action is not a good idea. The action does not include a parameter 'namespace', so
# in the case you want to use composition and load the gzserver into an already existing container.
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
# 3. Using the same node 'parameter_bridge' from the package 'ros_gz_bridge', but using the arguments instead of
# parameters.
# Node(
#         package='ros_gz_bridge',
#         executable='parameter_bridge',
#         name='clock_gz_bridge',
#         output='screen'4188202149517441,
#         # Descriptions at:
#         # Reference: https://github.com/gazebosim/ros_gz/tree/77522600db37d49a23e349c6e109b08caa621188/ros_gz_bridge#readme
#         # Referente: https://github.com/gazebosim/ros_gz/blob/77522600db37d49a23e349c6e109b08caa621188/ros_gz_bridge/src/parameter_bridge.cpp#L30
#         arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
#     )
# 4. Using the executable directly, like we do in this launch file.
# Method 3 is less preferred, since it can't specify all the options, like the other methods, just by using the format
# '<topic_name>@<ros_type_name><direction><gz_type_name>'.


def generate_launch_description():
    # (L)aunch (d)escription (e)ntitie(s)
    ldes: list[LaunchDescriptionEntity] = []

    ldes += [
        DeclareLaunchArgument(name='namespace', default_value='', description='Namespace'),
        DeclareLaunchArgument(
            'gui',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Run Gazebo Sim with GUI. If False, run in headless mode (default: False)',
        ),
        DeclareLaunchArgument(
            'initial_sim_time', default_value='0.0', description='Initial simulation time in seconds (default: 0.0)'
        ),
        DeclareLaunchArgument('gui_config_file', default_value='', description='Gazebo GUI configuration file to load'),
        DeclareLaunchArgument(
            'world_file', default_value='empty.sdf', description='World file w/o parent path (default: empty.sdf)'
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
            'autostart',
            default_value='True',
            choices=['True', 'true', 'False', 'false'],
            description='Run simulation on start. Available if use_composition is False (default: True)',
        ),
        DeclareLaunchArgument(
            'update_rate',
            default_value='',
            description='Update rate in Hertz. Available if use_composition is False (default: ?)',
        ),
        # For more information about composition when using ROS2 + Gazebo, visit the URL
        # 'https://gazebosim.org/docs/harmonic/ros2_overview/#composition'
        DeclareLaunchArgument(
            'use_composition',
            default_value='false',
            choices=['True', 'true', 'False', 'false'],
            description='Use compose bringup if True for the Gazebo server (default: False)',
        ),
        DeclareLaunchArgument(
            'create_own_container',
            default_value='True',
            choices=['True', 'true', 'False', 'false'],
            description='Whether we should start our own ROS container when using composition.',
        ),
        DeclareLaunchArgument(
            'container_name',
            default_value='rosgz_container',
            description='Name of container that nodes will load in if use composition',
        ),
        DeclareLaunchArgument(
            'respawn_clock_bridge',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Whether to respawn the clock bridge if it dies (default: False)',
        ),
        DeclareLaunchArgument(
            'clock_bridge_log_level',
            default_value='info',
            choices=['debug', 'info', 'warn', 'error'],
            description='Log level for the clock bridge (default: info)',
        ),
        OpaqueFunction(function=set_environment_variables),
    ]

    use_composition = LaunchConfiguration('use_composition')

    ldes += [
        SetLaunchConfiguration('bridge_name', 'rosgz_bridge_clock'),
        OpaqueFunction(function=create_composable_nodes, condition=IfCondition(use_composition)),
        OpaqueFunction(function=create_standard_nodes, condition=UnlessCondition(use_composition)),
    ]

    return LaunchDescription(ldes)


# ----------------------------------------------------------------------------------------------------------------------


# Opaque functions.


def create_composable_nodes(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """
    Create the Gazebo server and the clock bridge using composable nodes.
    """

    # From this line onwards, we apend to the 'actions' list of actions to launch Gazebo server (GUI optional) and
    # the clock bridge.

    # (L)aunch (d)escription (e)ntitie(s)
    ldes: list[LaunchDescriptionEntity] = []

    # If the user wants to run Gazebo Sim in headless mode, we do not launch the GUI.
    # If the user also wants Gazebo's GUI, we launch the GUI with the configuration file specified by the user, or
    # with the default configuration file 'eut_gz_models/config/gui.config' if the user does not specify a
    # configuration file.

    # Check if the Gazebo GUI must be launched.
    gui = perform_typed_substitution(ctx, normalize_typed_substitution(LaunchConfiguration('gui'), bool), bool)

    if gui:
        gz_args: list[str | Substitution] = ['-g']  # Start only the GUI client.
        gui_config_file = LaunchConfiguration('gui_config_file').perform(ctx)

        if gui_config_file:
            gz_args.extend([' --gui-config ', gui_config_file])

        # The following include does not run a ROS node, it launches an executable 'ruby $(which gz) sim ...', (see
        # ros_gz_sim/launch/gz_sim.launch.py), so the 'use_sim_time' and namespace parameters are not understood by
        # this executable.
        ldes.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
                ),
                launch_arguments={'gz_args': gz_args}.items(),
            )
        )

    container_name = LaunchConfiguration('container_name').perform(ctx)
    namespace = LaunchConfiguration('namespace').perform(ctx)

    create_own_container = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('create_own_container'), bool), bool
    )

    # Check if a new container is required or not.
    if create_own_container:
        # Append the new created container.
        ldes.append(
            Node(
                package='rclcpp_components',
                executable='component_container',
                name=container_name,
                namespace=namespace,
                output='screen',
            )
        )

    if namespace in ('', '/'):
        target_container = namespace + container_name
    else:
        # Make sure the namespace does not end with a slash, to avoid '//' in the target_container name.
        # Once we are sure no trailing '/' is present, we can concatenate the namespace, a '/' and the container name.
        target_container = namespace.rstrip('/') + '/' + container_name

    bridge_name = LaunchConfiguration('bridge_name').perform(ctx)

    # Composable nodes that are launched in a just created container, or in an existing container.
    ldes.append(
        LoadComposableNodes(
            target_container=target_container,
            composable_node_descriptions=[
                ComposableNode(
                    package='ros_gz_sim',
                    plugin='ros_gz_sim::GzServer',
                    name='rosgz_server',
                    namespace=namespace,
                    parameters=[
                        {
                            'world_sdf_file': LaunchConfiguration('world_file').perform(ctx),
                            'world_sdf_string': '',
                            # The gzserver requires the initial_sim_time parameter to be a float.
                            'initial_sim_time': perform_typed_substitution(
                                ctx, normalize_typed_substitution(LaunchConfiguration('initial_sim_time'), float), float
                            ),
                            # 'use_sim_time': , # No need to use for a node that does no access time.
                        }
                    ],
                    extra_arguments=[{'use_intra_process_comms': True}],
                ),
                ComposableNode(
                    package='ros_gz_bridge',
                    plugin='ros_gz_bridge::RosGzBridge',
                    name=bridge_name,
                    namespace=namespace,
                    parameters=[get_bridge_params(bridge_name)],
                    extra_arguments=[{'use_intra_process_comms': True}],
                ),
            ],
        )
    )

    return ldes


def create_standard_nodes(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """
    Create the Gazebo server and the clock bridge standard nodes.
    """
    # Standard node configuration
    # When no using composition, it makes more sense to use directy the 'gz sim' command, instead of using
    # the Node 'gzserver', since the 'gzserver' node does no include some interesting parameters that we
    # can pass to the 'gz sim' command, like:
    # - The verbosity level, from 0 to 4. The gzserver node that launches the Gazebo server sets the
    #   verbosity level to a fix value of 4 (too verbose).
    # - Autostart flag, to control whether the simulation starts automatically or not.
    # - The update rate in Hertz.
    # There are many more parameters that can be passed to the 'gz sim' command, but these are what I find
    # more useful for a regular basis use.
    # To check the parameters that can be passed to the 'gz sim' command, you can run:
    # gz sim --help
    gz_args: list[str] = []

    # If the user wants to run Gazebo Sim in headless mode, we do not launch the GUI.
    # If the user also wants Gazebo's GUI, we launch the GUI with the configuration file specified by the user, or
    # with the default configuration file 'eut_gz_models/config/gui.config' if the user does not specify a
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
            [' --gui-config ', os.path.join(get_package_share_directory('eut_gz_models'), 'config', 'gui.config')]
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

    gz_args.extend(
        [
            ' --initial-sim-time ',
            LaunchConfiguration('initial_sim_time').perform(ctx),
            ' -v',
            LaunchConfiguration('verbosity').perform(ctx),
            ' ',
            LaunchConfiguration('world_file').perform(ctx),
        ]
    )

    bridge_name = LaunchConfiguration('bridge_name').perform(ctx)

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
            name=bridge_name,
            namespace=LaunchConfiguration('namespace'),
            output='screen',
            respawn=LaunchConfiguration('respawn_clock_bridge'),
            respawn_delay=2.0,
            parameters=[get_bridge_params(bridge_name)],
            arguments=['--ros-args', '--log-level', LaunchConfiguration('clock_bridge_log_level')],
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

    # To spawn a world in Gazebo Sim, you just pass proper value in the parameter 'world_file', like 'empty.sdf' (in
    # default path for Gazebo), or 'sky.sdf' (in default path for Gazebo), or 'maze.sdf' (in eut_gz_models/worlds).

    # We need to set the GZ_SIM_RESOURCE_PATH environment variable properly to find the meshes used in the
    # robot_description topics.
    # If you want Gazebo to find the meshes of your robot, you need to add to the GZ_SIM_RESOURCE_PATH environment
    # variable the paths listed in the environment variable AMENT_PREFIX_PATH + 'share'.

    ament_prefix_path = os.getenv('AMENT_PREFIX_PATH', default='')

    resource_paths: list[str] = []

    if ament_prefix_path:
        resource_paths.extend([os.path.join(p, 'share') for p in ament_prefix_path.split(os.pathsep)])
        # print(f'Resource paths = {os.pathsep.join(resource_paths)}')

    # All paths, without duplicates.
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


# Non-opaque functions


def get_bridge_params(bridge_name: str):
    return {
        'subscription_heartbeat': 1000,  # default value in 'ros_gz_bridge.cpp'
        'expand_gz_topic_names': True,
        'bridge_names': [bridge_name],
        f'bridges.{bridge_name}.ros_topic_name': '/clock',
        f'bridges.{bridge_name}.gz_topic_name': '/clock',
        f'bridges.{bridge_name}.ros_type_name': 'rosgraph_msgs/msg/Clock',
        f'bridges.{bridge_name}.gz_type_name': 'gz.msgs.Clock',
        f'bridges.{bridge_name}.direction': 'GZ_TO_ROS',
        f'bridges.{bridge_name}.qos_profile': 'CLOCK',
        # Lazy subscription policy
        # Many bridges default to 'lazy: true' to avoid spinning up internal publishers/subscribers unless a
        # real client appears on the opposite side.
        # lazy = true  -> the bridge activates only when at least one ROS-side or GZ-side subscriber/publisher
        #                 exists, saving CPU/bandwidth.
        # lazy = false -> the bridge stays permanently connected, forwarding every message even if no node is
        #                 currently listening.
        # For /clock in simulation we normally force 'lazy: false' so the time source is always available as
        # soon as any ROS node starts.  For secondary topics,
        f'bridges.{bridge_name}.lazy': False,
    }


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
