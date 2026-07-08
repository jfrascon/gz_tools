"""
Spawn one model into a Gazebo world.

This launch file is inspired in the file
`/opt/ros/jazzy/share/ros_gz_sim/launch/gz_spawn_model.launch.py`.
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
            DeclareLaunchArgument('file', default_value='', description='SDF filename'),
            DeclareLaunchArgument('model_string', default_value='', description='XML(SDF) string'),
            DeclareLaunchArgument('topic', default_value='', description='Get XML from this topic'),
            DeclareLaunchArgument('entity_name', description='Name assigned to the spawned Gazebo entity'),
            DeclareLaunchArgument(
                'allow_renaming', default_value='False', description='Whether the entity allows renaming or not'
            ),
            DeclareLaunchArgument('x', default_value='0.0', description='Initial robot X position in meters'),
            DeclareLaunchArgument('y', default_value='0.0', description='Initial robot Y position in meters'),
            DeclareLaunchArgument('z', default_value='0.0', description='Initial robot Z position in meters'),
            DeclareLaunchArgument('R', default_value='0.0', description='Initial robot roll in radians'),
            DeclareLaunchArgument('P', default_value='0.0', description='Initial robot pitch in radians'),
            DeclareLaunchArgument('Y', default_value='0.0', description='Initial robot yaw in radians'),
            DeclareLaunchArgument(
                'node_output',
                default_value='both',
                choices=['both', 'screen', 'log', 'own_log', 'full'],
                description='Output configuration for the ros_gz_sim create process',
            ),
            DeclareLaunchArgument(
                'node_emulate_tty',
                default_value='False',
                choices=['False', 'True'],
                description='Whether to emulate a terminal for the ros_gz_sim create process',
            ),
            DeclareLaunchArgument(
                'node_log_level',
                default_value='info',
                choices=['debug', 'info', 'warn', 'error', 'fatal'],
                description='ROS log level passed to the ros_gz_sim create process',
            ),
            LogInfo(
                msg=[
                    "Spawning model '",
                    LaunchConfiguration('entity_name'),
                    "' into the world '",
                    LaunchConfiguration('world_name'),
                    "'",
                ]
            ),
            Node(
                package='ros_gz_sim',
                executable='create',
                parameters=[
                    {
                        'world': LaunchConfiguration('world_name'),
                        'file': LaunchConfiguration('file'),
                        'string': LaunchConfiguration('model_string'),
                        'topic': LaunchConfiguration('topic'),
                        'name': LaunchConfiguration('entity_name'),
                        'allow_renaming': LaunchConfiguration('allow_renaming'),
                        'x': LaunchConfiguration('x'),
                        'y': LaunchConfiguration('y'),
                        'z': LaunchConfiguration('z'),
                        'R': LaunchConfiguration('R'),
                        'P': LaunchConfiguration('P'),
                        'Y': LaunchConfiguration('Y'),
                    }
                ],
                arguments=['--ros-args', '--log-level', LaunchConfiguration('node_log_level')],
                output=LaunchConfiguration('node_output'),
                emulate_tty=LaunchConfiguration('node_emulate_tty'),
            ),
        ]
    )
