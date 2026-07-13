"""
Remove one model from a Gazebo world.

This launch file is inspired in the file
`/opt/ros/jazzy/share/ros_gz_sim/launch/gz_remove_model.launch.py`.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Declare the launch arguments consumed by the generic model remover."""
    return LaunchDescription(
        [
            DeclareLaunchArgument('world_name', description='Gazebo world where the model will be removed'),
            DeclareLaunchArgument('model_entity_name', description='Name of the Gazebo entity to remove'),
            DeclareLaunchArgument(
                'model_remove_node_output',
                default_value='both',
                choices=['both', 'screen', 'log', 'own_log', 'full'],
                description='Output configuration for the ros_gz_sim remove process',
            ),
            DeclareLaunchArgument(
                'model_remove_node_log_level',
                default_value='info',
                choices=['debug', 'info', 'warn', 'error', 'fatal'],
                description='ROS log level passed to the ros_gz_sim remove process',
            ),
            LogInfo(
                msg=[
                    "Removing model '",
                    LaunchConfiguration('model_entity_name'),
                    "' from the world '",
                    LaunchConfiguration('world_name'),
                    "'",
                ]
            ),
            Node(
                package='ros_gz_sim',
                executable='remove',
                parameters=[
                    {
                        'world': LaunchConfiguration('world_name'),
                        'entity_name': LaunchConfiguration('model_entity_name'),
                    }
                ],
                output=LaunchConfiguration('model_remove_node_output'),
                ros_arguments=['--log-level', LaunchConfiguration('model_remove_node_log_level')],
            ),
        ]
    )
