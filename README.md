# [`ros_gz_tools`](https://github.com/jfrascon/ros_gz_tools)

`ros_gz_tools` is a ROS 2 package that provides two kinds of content:

- Gazebo Sim resources owned by the package:
  - worlds under `worlds/`
  - models under `models/`
  - meshes under `meshes/`
  - GUI configuration under `config/`
- Reusable launch helpers for Gazebo world bringup:
  - `launch/spawn_world.launch.py`
  - `launch/spawn_gui.launch.py`
  - `launch/spawn_model.launch.py`
  - `launch/remove_model.launch.py`

The package is intentionally generic. It does not contain project-specific
robot orchestration. A project package can consume these launchers and pass its
own SDF world and bridge YAML files.

## Runtime Behavior

The runtime entry points are:

- `launch/spawn_world.launch.py`
- `launch/spawn_gui.launch.py`
- `launch/spawn_model.launch.py`
- `launch/remove_model.launch.py`

`spawn_world.launch.py` performs this sequence:

1. Read one SDF file that defines the world to launch.
2. Read one YAML file that defines the ROS-Gazebo bridges.
3. Start the Gazebo server through `ros_gz_sim.actions.GzServer`.
4. Optionally start the Gazebo GUI as a separate client process.

`spawn_world.launch.py` starts the world bridge through
`ros_gz_bridge.actions.RosGzBridge`. It uses `world_bridge_file` as the
project-facing name for the bridge YAML file and passes it to the bridge as
`config_file`. It also exposes typed bridge parameters for
`bridge_subscription_heartbeat`, `bridge_expand_gz_topic_names`,
`bridge_override_timestamps_with_wall_time`, and `bridge_override_frame_id`.

`spawn_gui.launch.py` starts only the Gazebo GUI client with `gz sim -g`.
It does not start the Gazebo server and it does not create bridges.

`spawn_model.launch.py` and `remove_model.launch.py` wrap the corresponding
`ros_gz_sim` model creation and removal nodes for dynamic Gazebo entity
management after a world is running.

## Dependencies

At runtime, this package depends on:

- `ros_gz_sim`
- `ros_gz_bridge`
- `ros2_launch_helpers`

`ros2_launch_helpers` is not expected to come from the system packages. The
repository therefore ships its own [deps.repos](deps.repos) file so the source
dependency can be fetched with `vcs import` when `ros_gz_tools` is used as a
standalone repository.

The dependency is still declared in `package.xml`. `deps.repos` complements
`package.xml`; it does not replace it.

## Gazebo Resource Resolution

This package uses both of these URI patterns inside SDF files:

- `package://ros_gz_tools/...`
- `model://<model_name>/...`

Because both forms are used, the package exports two Gazebo search roots:

- `share/` for `package://ros_gz_tools/...`
- `share/ros_gz_tools/models` for `model://<model_name>/...`

Those exports are declared in `package.xml`, and the environment hook keeps
the same paths available in sourced workspaces.

## Maintenance Scripts

The repository also contains scripts that are used only to generate or rebuild
package-owned assets, for example:

- `scripts/build_stl_from_png.py`
- `scripts/build_stl_from_png.sh`
- `meshes/office_environment_1/build_office_environment_1.sh`

These files are not part of the runtime contract of the package:

- they are not installed as runtime executables
- they are not invoked by the launch files
- they may require extra system packages or Python packages that are not
  declared as runtime dependencies in `package.xml`

Their purpose is to keep generated assets reproducible inside the repository.

## Building

Build the package inside a sourced ROS 2 workspace:

```bash
colcon build --merge-install --symlink-install --packages-select ros_gz_tools
source install/setup.bash
```

## Example Usage

Launch a world and its bridges:

```bash
ros2 launch ros_gz_tools spawn_world.launch.py \
  world_sdf_file:=/absolute/path/to/world.sdf \
  world_bridge_file:=/absolute/path/to/world_bridge.yaml \
  use_gz_gui:=True
```

Launch only the Gazebo GUI client:

```bash
ros2 launch ros_gz_tools spawn_gui.launch.py \
  gz_gui_config_file:=package://ros_gz_tools/config/gz_gui.config
```
