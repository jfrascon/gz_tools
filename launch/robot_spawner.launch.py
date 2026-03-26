import os

from launch_ros.actions import Node

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction, SetLaunchConfiguration
from launch.substitutions import LaunchConfiguration

# This launch spawns a robot entity in an already running Gazebo world from a
# ROS topic that publishes the robot description.
#
# The package intentionally launches `ros_gz_sim/create` directly instead of
# reusing `ros_gz_sim` higher-level spawn launch files.
#
# `ros_gz_sim` already ships a launch flow for spawning models. Internally that
# flow ends up calling the same `create` executable that this file uses.
# However, the higher-level launch file also pulls in bridge-oriented behavior
# that this package does not want here. In this package, world launching,
# bridging, and robot spawning are kept as separate responsibilities.
# References:
# https://github.com/gazebosim/ros_gz/blob/ros2/ros_gz_sim/launch/gz_spawn_model.launch.py
# https://gazebosim.org/docs/harmonic/ros2_spawn_model/
#
# `world_file` is used only to derive the Gazebo world name. This file assumes
# `world name == world_file stem`. If the running Gazebo world uses a different
# name, the spawn request will target the wrong world.
#
# There is no need to wrap this file with `PushRosNamespace`. The `create`
# process performs the spawn request and then exits.


def generate_launch_description():
    ldes: list[LaunchDescriptionEntity] = []

    ldes += [
        DeclareLaunchArgument(
            'world_file',
            default_value='empty.sdf',
            description='World file name or absolute .sdf path used to derive the Gazebo world name',
        ),
        DeclareLaunchArgument(
            'topic', default_value='', description='Topic with robot description to spawn the robot in Gazebo Sim'
        ),
        DeclareLaunchArgument(
            'model_name', default_value='', description='Model name to spawn the robot in Gazebo Sim'
        ),
        DeclareLaunchArgument(
            'allow_renaming',
            default_value='False',
            choices=['True', 'False'],
            description='Rename entity if name already used (default: False)',
        ),
        DeclareLaunchArgument(
            'x', default_value='0.0', description='x position of the robot in Gazebo Sim (default: 0.0)'
        ),
        DeclareLaunchArgument(
            'y', default_value='0.0', description='y position of the robot in Gazebo Sim (default: 0.0)'
        ),
        DeclareLaunchArgument(
            'z', default_value='0.0', description='z position of the robot in Gazebo Sim (default: 0.0)'
        ),
        DeclareLaunchArgument(
            'R', default_value='0.0', description='roll position of the robot in Gazebo Sim (default: 0.0)'
        ),
        DeclareLaunchArgument(
            'P', default_value='0.0', description='pitch position of the robot in Gazebo Sim (default: 0.0)'
        ),
        DeclareLaunchArgument(
            'Y', default_value='0.0', description='yaw position of the robot in Gazebo Sim (default: 0.0)'
        ),
        OpaqueFunction(function=get_world_from_world_file),
        LogInfo(
            msg=[
                "Spawning robot from topic '",
                LaunchConfiguration('topic'),
                "' into the world '",
                LaunchConfiguration('world'),
                "'",
            ]
        ),
        Node(
            package='ros_gz_sim',
            executable='create',
            output='screen',
            arguments=[
                '-world',
                LaunchConfiguration('world'),
                '-topic',
                LaunchConfiguration('topic'),
                '-name',
                LaunchConfiguration('model_name'),
                '-allow_renaming',
                LaunchConfiguration('allow_renaming'),
                '-x',
                LaunchConfiguration('x'),
                '-y',
                LaunchConfiguration('y'),
                '-z',
                LaunchConfiguration('z'),
                '-R',
                LaunchConfiguration('R'),
                '-P',
                LaunchConfiguration('P'),
                '-Y',
                LaunchConfiguration('Y'),
            ],
        ),
    ]

    return LaunchDescription(ldes)


def get_world_from_world_file(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """
    Derive the Gazebo world name from the `world_file` launch argument.

    The derived name is the file stem, for example `office.sdf -> office`.
    This matches the convention used by the worlds shipped in this package.
    """
    world_file = LaunchConfiguration('world_file').perform(ctx)

    return [SetLaunchConfiguration('world', os.path.splitext(world_file)[0])]
