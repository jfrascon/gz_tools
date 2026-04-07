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
  - `scripts/wait_for_gz_service.py`

The package is intentionally generic. It does not contain project-specific
robot orchestration. A project package can consume these launchers and pass its
own YAML files for world, obstacle, and bridge configuration.

## Runtime Behavior

The runtime entry points are:

- `launch/spawn_world.launch.py`
- `launch/spawn_gui.launch.py`
- `scripts/wait_for_gz_service.py`

`spawn_world.launch.py` performs this sequence:

1. Read one YAML file that defines the world and the fixed obstacles to spawn.
2. Read one YAML file that defines the ROS-Gazebo bridges.
3. Start the Gazebo server through `ros_gz_sim.launch.py`.
4. Optionally start the Gazebo GUI as a separate client process.
5. Wait until Gazebo exposes `/world/<world_name>/create`.
6. Spawn each enabled obstacle through `ros_gz_sim/gz_spawn_model.launch.py`.

`spawn_gui.launch.py` starts only the Gazebo GUI client with `gz sim -g`.
It does not start the Gazebo server and it does not create bridges.

`wait_for_gz_service.py` is a small helper used by the launch files. It polls
`gz service -l` until a requested Gazebo Transport service appears.

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

Launch a world, its bridges, and the fixed obstacles defined by a project
package:

```bash
ros2 launch ros_gz_tools spawn_world.launch.py \
  simulation_world_obstacles_file:=package://simulation/config/simulation_world_obstacles.yaml \
  simulation_world_bridge_file:=package://simulation/config/simulation_bridge.yaml \
  gz_gui:=True
```

Launch only the Gazebo GUI client:

```bash
ros2 launch ros_gz_tools spawn_gui.launch.py \
  gz_gui_config_file:=package://ros_gz_tools/config/gz_gui.config
```
