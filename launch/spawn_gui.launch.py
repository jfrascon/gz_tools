"""
Launch the Gazebo Sim GUI as a separate client process.

This launch file starts only the Gazebo GUI client by running `gz sim -g`.
It does not start the Gazebo server and it does not create ROS-Gazebo bridges.

The intended use is to pair this launcher with a separate server bringup, such
as `spawn_world.launch.py`, when rendering should stay independent from the
simulation backend.
"""

from pathlib import Path

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    """
    Declare the GUI arguments consumed by this launcher.

    Returns:
        LaunchDescription: Launch description with the GUI configuration
        argument and the opaque function that expands it into the GUI process.
    """
    return LaunchDescription(
        [
            # The GUI layout file is optional. When omitted, Gazebo uses its
            # default client layout.
            DeclareLaunchArgument(
                'gzgui_config_file', default_value='', description='Gazebo Sim GUI client configuration file'
            ),
            OpaqueFunction(function=_spawn_gui),
        ]
    )


def _spawn_gui(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """Build the process action that starts the Gazebo GUI-only client.

    Args:
        ctx: Launch context used to resolve LaunchConfiguration values.

    Returns:
        list[LaunchDescriptionEntity]: A single ExecuteProcess action that
        starts `gz sim -g` with an optional GUI layout file.
    """
    # Start from the GUI-only Gazebo command. This launcher never starts the
    # server because the server is expected to be launched elsewhere.
    gui_config_file = LaunchConfiguration('gzgui_config_file').perform(ctx)
    gui_cmd = ['gz', 'sim', '-g']

    # If the caller provided a GUI layout file, validate it early and pass it
    # through to Gazebo so failures happen before the process starts.
    if gui_config_file:
        if not Path(gui_config_file).is_file():
            raise FileNotFoundError(f"GUI config file '{gui_config_file}' not found")

        gui_cmd.extend(['--gui-config', gui_config_file])

    return [ExecuteProcess(cmd=gui_cmd, output='screen')]
