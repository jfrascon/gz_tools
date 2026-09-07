"""
Remove one model from a Gazebo world.

This launch file is inspired in the file
`/opt/ros/jazzy/share/ros_gz_sim/launch/gz_remove_model.launch.py`.
"""

from launch import LaunchContext
from launch import LaunchDescription
from launch import LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument
from launch.actions import LogInfo
from launch.actions import OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import ros2_launch_helpers as rlh


def generate_launch_description() -> LaunchDescription:
    """Declare the launch arguments consumed by the generic model remover."""
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'world_name', description='Gazebo world where the model will be removed.'
            ),
            DeclareLaunchArgument(
                'model_entity_name', description='Name of the Gazebo entity to remove.'
            ),
            DeclareLaunchArgument(
                'node_args',
                default_value='{"output":"both","ros_arguments":["--log-level","info"]}',
                description=rlh.LAUNCH_ACTION_ARGUMENTS_DESC,
            ),
            OpaqueFunction(function=_remove_model),
        ]
    )


def _remove_model(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """Validate the removal request and create the Gazebo model-removal actions."""
    world_name = LaunchConfiguration('world_name').perform(ctx)
    model_entity_name = LaunchConfiguration('model_entity_name').perform(ctx)

    if not world_name.strip():
        raise ValueError("Launch argument 'world_name' must identify a Gazebo world.")

    if not model_entity_name.strip():
        raise ValueError("Launch argument 'model_entity_name' must identify the Gazebo entity.")

    return [
        LogInfo(msg=f"Removing model '{model_entity_name}' from world '{world_name}'"),
        Node(
            package='ros_gz_sim',
            executable='remove',
            parameters=[{'world': world_name, 'entity_name': model_entity_name}],
            **rlh.resolve_node_arguments(LaunchConfiguration('node_args').perform(ctx)),
        ),
    ]
