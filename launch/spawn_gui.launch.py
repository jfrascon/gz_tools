"""
Launch the Gazebo Sim GUI as a separate client process.

This launch file starts only the Gazebo GUI client by running `gz sim -g`.
It does not start the Gazebo server or create ROS-Gazebo bridges.

Pair this launcher with a separate server bringup, such as `spawn_world.launch.py`, when rendering
must remain independent from the simulation backend.
"""

from pathlib import Path

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    """Declare the GUI configuration and the action that starts the client process."""
    return LaunchDescription(
        [
            # The GUI layout file is optional.
            # Gazebo uses its default client layout when the argument is empty.
            DeclareLaunchArgument(
                'gzgui_config_file',
                default_value='',
                description='Gazebo Sim GUI client configuration file.',
            ),
            OpaqueFunction(function=_spawn_gui),
        ]
    )


def _spawn_gui(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """Create the `gz sim -g` process with an optional GUI layout file."""
    # This launcher starts only the GUI client.
    # A separate launch file must start the Gazebo server.
    gui_config_file = LaunchConfiguration('gzgui_config_file').perform(ctx)
    gui_cmd = ['gz', 'sim', '-g']

    # Validate an explicit layout before starting Gazebo so a bad path fails immediately.
    if gui_config_file:
        if not Path(gui_config_file).is_file():
            raise FileNotFoundError(f"GUI config file '{gui_config_file}' not found")

        gui_cmd.extend(['--gui-config', gui_config_file])

    return [ExecuteProcess(cmd=gui_cmd, output='screen')]
