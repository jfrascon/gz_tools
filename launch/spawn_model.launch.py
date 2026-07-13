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
    """Declare the launch arguments consumed by the generic model spawner."""
    return LaunchDescription(
        [
            DeclareLaunchArgument('world_name', description='Gazebo world where the model will be spawned'),
            DeclareLaunchArgument('model_sdf_file', default_value='', description='SDF filename'),
            DeclareLaunchArgument('model_sdf_string', default_value='', description='XML(SDF) string'),
            DeclareLaunchArgument('model_sdf_topic', default_value='', description='Get XML from this topic'),
            DeclareLaunchArgument('model_entity_name', description='Name assigned to the spawned Gazebo entity'),
            DeclareLaunchArgument(
                'model_allow_renaming',
                default_value='False',
                choices=['True', 'true', 'False', 'false'],
                description='Whether the entity allows renaming or not',
            ),
            DeclareLaunchArgument(
                'model_pose_x', default_value='0.0', description='Initial model X position in meters'
            ),
            DeclareLaunchArgument(
                'model_pose_y', default_value='0.0', description='Initial model Y position in meters'
            ),
            DeclareLaunchArgument(
                'model_pose_z', default_value='0.0', description='Initial model Z position in meters'
            ),
            DeclareLaunchArgument('model_pose_roll', default_value='0.0', description='Initial model roll in radians'),
            DeclareLaunchArgument(
                'model_pose_pitch', default_value='0.0', description='Initial model pitch in radians'
            ),
            DeclareLaunchArgument('model_pose_yaw', default_value='0.0', description='Initial model yaw in radians'),
            DeclareLaunchArgument(
                'model_spawn_node_output',
                default_value='both',
                choices=['both', 'screen', 'log', 'own_log', 'full'],
                description='Output configuration for the ros_gz_sim create process',
            ),
            DeclareLaunchArgument(
                'model_spawn_node_log_level',
                default_value='info',
                choices=['debug', 'info', 'warn', 'error', 'fatal'],
                description='ROS log level passed to the ros_gz_sim create process',
            ),
            LogInfo(
                msg=[
                    "Spawning model '",
                    LaunchConfiguration('model_entity_name'),
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
                        'file': LaunchConfiguration('model_sdf_file'),
                        'string': LaunchConfiguration('model_sdf_string'),
                        'topic': LaunchConfiguration('model_sdf_topic'),
                        'name': LaunchConfiguration('model_entity_name'),
                        'allow_renaming': LaunchConfiguration('model_allow_renaming'),
                        'x': LaunchConfiguration('model_pose_x'),
                        'y': LaunchConfiguration('model_pose_y'),
                        'z': LaunchConfiguration('model_pose_z'),
                        'R': LaunchConfiguration('model_pose_roll'),
                        'P': LaunchConfiguration('model_pose_pitch'),
                        'Y': LaunchConfiguration('model_pose_yaw'),
                    }
                ],
                ros_arguments=['--log-level', LaunchConfiguration('model_spawn_node_log_level')],
                output=LaunchConfiguration('model_spawn_node_output'),
            ),
        ]
    )
