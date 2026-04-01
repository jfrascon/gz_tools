"""
Launch a Gazebo Sim world, its bridges, and a list of fixed obstacles.

This launch file requires:
- one YAML file that defines which world to run and which fixed obstacles to
  insert into that world.
- one YAML file that defines the ROS-Gazebo bridges that must be created.

The launch file then performs the complete world bringup sequence:

- start the Gazebo server through `ros_gz_sim.launch.py`.
- optionally start the Gazebo GUI as a separate client process.
- wait until Gazebo exposes the `/world/<world_name>/create` service.
- spawn every enabled obstacle defined in the YAML configuration.

The file is intentionally generic. It does not know anything about a specific
project, robot, navigation stack, or scenario-level orchestration.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_prefix
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
    Shutdown,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity


def generate_launch_description() -> LaunchDescription:
    """
    Declare the launch arguments consumed by the generic world bringup.

    Returns:
        LaunchDescription: Launch description with all supported arguments and
        the opaque function that expands them into the real launch actions.
    """
    return LaunchDescription(
        [
            # Namespace and configuration file arguments define which ROS nodes
            # are created and which world/bridge YAML files are consumed.
            DeclareLaunchArgument(
                name='namespace', default_value='', description='Namespace for Gazebo-related ROS nodes'
            ),
            DeclareLaunchArgument(
                'simulation_world_obstacles_file',
                default_value='',
                description='YAML file that defines the world and fixed obstacles to insert into it',
            ),
            DeclareLaunchArgument(
                'simulation_world_bridge_file',
                default_value='',
                description='YAML file used to configure ros_gz_bridge for the simulation world',
            ),
            # GUI arguments control whether Gazebo rendering runs as a separate
            # client process and which GUI layout file it should use.
            DeclareLaunchArgument(
                'gz_gui',
                default_value='True',
                choices=['True', 'true', 'False', 'false'],
                description='Launch Gazebo Sim GUI client. If False, Gazebo Sim runs in headless mode',
            ),
            DeclareLaunchArgument(
                'gz_gui_config_file', default_value='', description='Gazebo Sim GUI client configuration file'
            ),
            # Wait arguments tune how long the launch file waits for Gazebo to
            # expose the world create service before obstacle spawning starts.
            DeclareLaunchArgument(
                'gz_service_wait_timeout',
                default_value='60.0',
                description='Maximum time in seconds to wait for the Gazebo create service before failing',
            ),
            DeclareLaunchArgument(
                'gz_service_wait_poll_period',
                default_value='0.25',
                description='Polling period in seconds between Gazebo service availability checks',
            ),
            OpaqueFunction(function=_spawn_world),
        ]
    )


def _get_world_name(world_file: str) -> str:
    """
    Return the internal Gazebo world name defined in an SDF file.

    Gazebo services such as `/world/<world_name>/create` use the `<world>`
    name stored inside the SDF document.

    Args:
        world_file: Absolute path to the SDF world file.

    Returns:
        str: The world name stored in the `<world name="...">` element.
    """
    # Gazebo service names use the internal SDF world name. They do not use
    # the file name on disk, so the launcher must read the SDF document.
    root = ET.parse(world_file).getroot()
    world = root.find('world')

    if world is None:
        raise ValueError(f"World file '{world_file}' does not contain a <world> element")

    world_name = world.get('name')

    if not world_name:
        raise ValueError(f"World file '{world_file}' does not define a name in its <world> element")

    return world_name


def _spawn_world(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """
    Build the actions that start Gazebo and spawn the configured obstacles.

    The function resolves the YAML files passed through launch arguments,
    validates their contents, launches the Gazebo backend, optionally launches
    the GUI client, and finally schedules obstacle insertion after the Gazebo
    world create service becomes available.

    Args:
        ctx: Launch context used to resolve LaunchConfiguration values.

    Returns:
        list[LaunchDescriptionEntity]: Launch actions for world bringup, GUI,
        wait helper, and obstacle insertion.
    """
    # Resolve and validate the YAML file that defines which world to run and
    # which fixed obstacles should later be inserted into it.
    simulation_world_obstacles_file = LaunchConfiguration('simulation_world_obstacles_file').perform(ctx).strip()

    if not simulation_world_obstacles_file:
        raise ValueError("Launch argument 'simulation_world_obstacles_file' cannot be empty")

    resolved_sim_world_obstacles_file, simulation_cfg = rlh.read_yaml_file(simulation_world_obstacles_file)

    if simulation_cfg is None:
        raise ValueError(f"Simulation configuration file '{resolved_sim_world_obstacles_file}' is empty")

    if not isinstance(simulation_cfg, dict):
        raise ValueError(
            f"Simulation configuration file '{resolved_sim_world_obstacles_file}' must be a mapping. "
            f"Got: '{type(simulation_cfg).__name__}'"
        )

    # Resolve and validate the SDF world file referenced by the YAML mapping.
    # This file is passed to `ros_gz_sim.launch.py` as `world_sdf_file`.
    world_file = simulation_cfg.get('world')

    if not isinstance(world_file, str) or not world_file.strip():
        raise ValueError(
            f"Key 'world' in file '{resolved_sim_world_obstacles_file}' must have a non-empty string value"
        )

    resolved_world_file = rlh.resolve_file(world_file.strip())

    if not resolved_world_file:
        raise FileNotFoundError(
            f"World file '{world_file}' from '{resolved_sim_world_obstacles_file}' could not be resolved"
        )

    if not Path(resolved_world_file).is_file():
        raise FileNotFoundError(f"World file '{resolved_world_file}' not found")

    # Resolve and validate the bridge YAML file. This file stays independent
    # from the world-obstacles YAML so callers can decide whether both
    # configurations should be coupled or overridden independently.
    simulation_world_bridge_file = LaunchConfiguration('simulation_world_bridge_file').perform(ctx).strip()

    if not simulation_world_bridge_file:
        raise ValueError("Launch argument 'simulation_world_bridge_file' cannot be empty")

    resolved_bridge_file = rlh.resolve_file(simulation_world_bridge_file)

    if not resolved_bridge_file:
        raise FileNotFoundError(f"Bridge file '{simulation_world_bridge_file}' could not be resolved")

    if not Path(resolved_bridge_file).is_file():
        raise FileNotFoundError(f"Resolved bridge file '{resolved_bridge_file}' not found")

    # Read metadata needed later in the launch flow:
    # - `world_name` is required to build the Gazebo create service name
    # - `obstacles` is the list of user-defined obstacle entries
    world_name = _get_world_name(resolved_world_file)
    obstacles = simulation_cfg.get('obstacles', [])

    # Build a bridge name that stays unique when the launch runs under a
    # namespace, while keeping the plain `world_bridge` name for the root case.
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    bridge_name_prefix = ''

    if namespace not in ('', '/'):
        bridge_name_prefix = rlh.underscorify_namespace(namespace) + '_'

    bridge_name = bridge_name_prefix + 'world_bridge'

    if not isinstance(obstacles, list):
        raise TypeError(f"Key 'obstacles' in '{resolved_sim_world_obstacles_file}' must be a list")

    # Validate obstacle entries, skip the ones explicitly disabled, and build
    # the `gz_spawn_model.launch.py` includes that will later spawn them.
    obstacle_actions: list[LaunchDescriptionEntity] = []
    enabled_obstacle_names: set[str] = set()
    enabled_obstacle_count = 0

    for index, obstacle in enumerate(obstacles):
        if not isinstance(obstacle, dict):
            raise TypeError(f"Obstacle at index {index} in '{resolved_sim_world_obstacles_file}' must be a mapping")

        enabled = obstacle.get('enabled', True)

        if not isinstance(enabled, bool):
            raise TypeError(
                f"Obstacle at index {index} in '{resolved_sim_world_obstacles_file}' must define 'enabled' as a bool"
            )

        # Disabled obstacles stay in the YAML file for convenience, but they do
        # not produce any Gazebo action in this launch and do not need further
        # validation.
        if not enabled:
            continue

        name = obstacle.get('name')
        model_file = obstacle.get('path')
        pose = obstacle.get('pose')

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Obstacle at index {index} in '{resolved_sim_world_obstacles_file}' must define a non-empty 'name'"
            )

        obstacle_name = name.strip()

        # Enforce unique names among enabled obstacles so Gazebo spawn failures
        # are caught early with a clearer configuration error.
        if obstacle_name in enabled_obstacle_names:
            raise ValueError(f"Obstacle name '{obstacle_name}' is duplicated in '{resolved_sim_world_obstacles_file}'")

        enabled_obstacle_names.add(obstacle_name)
        enabled_obstacle_count += 1

        if not isinstance(model_file, str) or not model_file.strip():
            raise ValueError(
                f"Obstacle '{obstacle_name}' in '{resolved_sim_world_obstacles_file}' must define a non-empty 'path'"
            )

        if not isinstance(pose, dict):
            raise TypeError(
                f"Obstacle '{obstacle_name}' in '{resolved_sim_world_obstacles_file}' must define 'pose' as a mapping"
            )

        # Require the full pose so every spawn request is explicit. This avoids
        # accidental defaults that are hard to notice once the world is loaded.
        for coordinate in ('x', 'y', 'z', 'R', 'P', 'Y'):
            if coordinate not in pose:
                raise ValueError(
                    f"Obstacle '{obstacle_name}' in '{resolved_sim_world_obstacles_file}' is missing pose key "
                    f"'{coordinate}'"
                )

            if not isinstance(pose[coordinate], (int, float)):
                raise TypeError(
                    f"Obstacle '{obstacle_name}' in '{resolved_sim_world_obstacles_file}' has non-numeric pose "
                    f"'{coordinate}': {type(pose[coordinate]).__name__}"
                )

        resolved_model_file = rlh.resolve_file(model_file.strip())

        if not resolved_model_file:
            raise FileNotFoundError(
                f"Obstacle model file '{model_file}' for obstacle '{obstacle_name}' could not be resolved"
            )

        if not Path(resolved_model_file).is_file():
            raise FileNotFoundError(
                f"Resolved obstacle model file '{resolved_model_file}' for obstacle '{obstacle_name}' not found"
            )

        # Keep obstacle spawning aligned with the official ros_gz_sim launcher.
        obstacle_actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_spawn_model.launch.py'])
                ),
                launch_arguments={
                    'world': world_name,
                    'file': resolved_model_file,
                    'entity_name': obstacle_name,
                    'x': str(pose['x']),
                    'y': str(pose['y']),
                    'z': str(pose['z']),
                    'R': str(pose['R']),
                    'P': str(pose['P']),
                    'Y': str(pose['Y']),
                }.items(),
            )
        )

    # Start with the Gazebo backend include and a few logs that make it easier
    # to diagnose bad paths or unexpected launch argument values.
    launch_entities: list[LaunchDescriptionEntity] = [
        LogInfo(msg=f'Resolved world file: {resolved_world_file}'),
        LogInfo(msg=f'Resolved bridge file: {resolved_bridge_file}'),
        LogInfo(msg=f'Resolved world name: {world_name}'),
        LogInfo(msg=f'Launch GUI: {LaunchConfiguration("gz_gui").perform(ctx).strip()}'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'ros_gz_sim.launch.py'])
            ),
            launch_arguments={
                'namespace': LaunchConfiguration('namespace'),
                'bridge_name': bridge_name,
                'config_file': resolved_bridge_file,
                'world_sdf_file': resolved_world_file,
                'use_respawn': 'False',
                'bridge_log_level': 'info',
            }.items(),
        ),
    ]

    # Optionally start the GUI as a separate client process. This keeps the
    # simulation backend independent from the rendering frontend.
    launch_gui = LaunchConfiguration('gz_gui').perform(ctx).strip().lower() == 'true'

    if launch_gui:
        launch_entities.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([FindPackageShare('ros_gz_tools'), 'launch', 'spawn_gui.launch.py'])
                ),
                launch_arguments={'gz_gui_config_file': LaunchConfiguration('gz_gui_config_file')}.items(),
            )
        )

    if enabled_obstacle_count == 0:
        launch_entities.append(LogInfo(msg=f"No enabled obstacles to spawn into '{world_name}'"))
        return launch_entities

    # Wait for the Gazebo create service instead of sleeping for a fixed delay.
    # This makes obstacle insertion depend on actual server readiness rather
    # than on timing assumptions.
    service_name = f'/world/{world_name}/create'
    wait_script = os.path.join(get_package_prefix('ros_gz_tools'), 'lib', 'ros_gz_tools', 'wait_for_gz_service.py')
    wait_timeout = LaunchConfiguration('gz_service_wait_timeout').perform(ctx).strip()
    wait_poll_period = LaunchConfiguration('gz_service_wait_poll_period').perform(ctx).strip()
    wait_for_create_service = ExecuteProcess(
        cmd=['python3', wait_script, service_name, '--timeout', wait_timeout, '--poll-period', wait_poll_period],
        output='screen',
    )

    # `OnProcessExit` is used here because the wait helper is the explicit
    # synchronization point for obstacle insertion:
    # - return code 0 means Gazebo already exposes `/world/<world_name>/create`
    # - any other return code means waiting failed and the launch should stop
    #
    # The lambda is intentionally kept here instead of using a helper
    # function. The branching is small and it is easier to understand when the
    # success path and failure path stay next to the event handler.
    launch_entities.extend(
        [
            LogInfo(msg=f"Spawning {enabled_obstacle_count} enabled fixed obstacles into '{world_name}'"),
            wait_for_create_service,
            RegisterEventHandler(
                OnProcessExit(
                    target_action=wait_for_create_service,
                    on_exit=lambda event, _context: (
                        obstacle_actions
                        if event.returncode == 0
                        else [
                            Shutdown(
                                reason=(
                                    f"Service '{service_name}' did not become available. "
                                    f'wait_for_gz_service.py exited with code {event.returncode}'
                                )
                            )
                        ]
                    ),
                )
            ),
        ]
    )

    return launch_entities
