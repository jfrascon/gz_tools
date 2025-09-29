import os

from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction, SetLaunchConfiguration
from launch.substitutions import LaunchConfiguration

# THERE IS NO NEED TO PUSH THIS PYTHON LAUNCH FILE INTO A NAMESPACE, using PushRosNamespace, WHEN IT IS INCLUDED IN
# ANOTHER LAUNCH FILE, SINCE THE 'CREATE' EXECUTABLE INJECTS THE ROBOT DESCRIPTION INTO GAZEBO AND THEN IT STOPS
# RUNNING.
# This python launch file uses the node 'create' from the package 'ros_gz_sim' to spawn a robot in Gazebo Sim.

# IMPORTANT NOTE:
# We are considering that the 'world name' is the same as the 'world file name' without the extension.
# If this is not the case, the world will not be found in Gazebo Sim.

# If you are familiar with the package 'ros_gz_sim', you might know that there is a launch file in that package called
# 'ros_gz_spawn_model.launch.py' that is used to spawn a robot in Gazebo Sim.
# However, that launch file run also a RosGzBridge action to bridge the topics between ROS2 and Gazebo, for the sensors
# that the robot uses, like cameras, lidars, etc., among others.
# In our workflow, the bridges to transfer topics between Gazebo and ROS2 are launched should not be launched from
# the 'ros_gz_spawn_model.launch.py' launch file.
# For this reason, we do not use the launch file 'ros_gz_spawn_model.launch.py' and implement our own logic to spawn
# the robot in Gazebo Sim.
# If you look into the file 'ros_gz_spawn_model.launch.py', you will see that it uses:
# IncludeLaunchDescription(
#         PythonLaunchDescriptionSource(
#             [PathJoinSubstitution([FindPackageShare('ros_gz_sim'),
#                                    'launch',
#                                    'gz_spawn_model.launch.py'])]),
#         launch_arguments=[('world', world),
#                           ('file', file),
#                           ('model_string', model_string),
#                           ('topic', topic),
#                           ('entity_name', entity_name),
#                           ('allow_renaming', allow_renaming),
#                           ('x', x),
#                           ('y', y),
#                           ('z', z),
#                           ('R', roll),
#                           ('P', pitch),
#                           ('Y', yaw), ])
# and the 'gz_spawn_model.launch.py' file executes the 'create' node internally.
# To be honest, we could have used the 'gz_spawn_model.launch.py' by using an IncludeLaunchDescription action, like
# the one above, but having into account that writing the instructions to execute the 'create' node is not that
# difficult, we decided to launch the node 'create' directly.
# URL with example of spawning a model from the CLI:
# https://gazebosim.org/docs/harmonic/ros2_spawn_model/#spawn-a-model-using-the-launch-file-included-in-ros-gz-sim


def generate_launch_description():
    # (L)aunch (d)escription (e)ntities.
    ldes: list[LaunchDescriptionEntity] = []

    ldes += [
        DeclareLaunchArgument(
            'world_file', default_value='empty.sdf', description='World file w/o parent path (default: empty.sdf)'
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
            parameters=[
                {
                    # The world name is the same as the world file name w/o extension
                    'world': ParameterValue(LaunchConfiguration('world'), value_type=str),
                    # Load XML model from a topic
                    'topic': ParameterValue(LaunchConfiguration('topic'), value_type=str),
                    # Load XML model from a file not provided here.
                    # 'file': ParameterValue(LaunchConfiguration('file')),
                    # Load XML model from a ROS param not provided here.
                    # 'param': ParameterValue(LaunchConfiguration('param')),
                    # Load XML model from a ROS string not provided here.
                    # 'string': ParameterValue(LaunchConfiguration('string')),
                    'name': ParameterValue(LaunchConfiguration('model_name'), value_type=str),
                    'allow_renaming': ParameterValue(LaunchConfiguration('allow_renaming'), value_type=bool),
                    'x': ParameterValue(LaunchConfiguration('x'), value_type=float),
                    'y': ParameterValue(LaunchConfiguration('y'), value_type=float),
                    'z': ParameterValue(LaunchConfiguration('z'), value_type=float),
                    'R': ParameterValue(LaunchConfiguration('R'), value_type=float),
                    'P': ParameterValue(LaunchConfiguration('P'), value_type=float),
                    'Y': ParameterValue(LaunchConfiguration('Y'), value_type=float),
                }
            ],
        ),
    ]

    return LaunchDescription(ldes)


def get_world_from_world_file(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """
    Get the world name from the world file.
    We are considering that the world name is the same as the world file name without the extension.
    If this is not the case, the world will not be found in Gazebo Sim.
    """
    world_file = LaunchConfiguration('world_file').perform(ctx)

    return [SetLaunchConfiguration('world', os.path.splitext(world_file)[0])]
