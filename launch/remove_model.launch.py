"""
Spawn one model into a Gazebo world.

This launch file is inspired in the file
`/opt/ros/jazzy/share/ros_gz_sim/launch/gz_remove_model.launch.py`.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Declare the launch arguments consumed by the generic robot spawner."""
    return LaunchDescription(
        [
            DeclareLaunchArgument('world_name', description='Gazebo world where the robot will be spawned'),
            DeclareLaunchArgument('entity_name', description='Name assigned to the spawned Gazebo entity'),
            DeclareLaunchArgument(
                'node_output',
                default_value='screen',
                description='Output configuration for the ros_gz_sim create process',
            ),
            LogInfo(
                msg=[
                    "Removing model '",
                    LaunchConfiguration('entity_name'),
                    "' from the world '",
                    LaunchConfiguration('world_name'),
                    "'",
                ]
            ),
            Node(
                package='ros_gz_sim',
                executable='remove',
                parameters=[
                    {'world': LaunchConfiguration('world_name'), 'entity_name': LaunchConfiguration('entity_name')}
                ],
                output=LaunchConfiguration('node_output'),
            ),
        ]
    )
