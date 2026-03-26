# ros_gz_tools

`ros_gz_tools` is a ROS 2 package that groups Gazebo Sim resources and the launch files used to run them.
The package installs:

- SDF worlds under `worlds/`
- Gazebo models under `models/`
- Mesh assets and source files under `meshes/`
- Launch files under `launch/`
- Helper scripts under `scripts/`
- A Gazebo GUI configuration under `config/`
- A colcon environment hook under `hooks/`

The package is meant to solve two concrete problems:

1. Launch a Gazebo world from ROS 2 with the resource paths already configured.
2. Keep package-owned simulation assets reproducible, especially worlds that are generated from floor-plan images.

## Prerequisites

Use this package from a sourced ROS 2 workspace that already provides Gazebo Sim integration.
At minimum, the sourced environment must include:

- `ros_gz_sim`
- `ros_gz_bridge`

## Quickstart

Build and source the workspace:

```bash
cd <workspace_path>
colcon build --merge-install --symlink-install
source install/setup.bash
```

Launch the office world with the Gazebo GUI:

```bash
ros2 launch ros_gz_tools world_spawner.launch.py \
  world_file:=office_environment_1.sdf \
  gui:=True
```

Launch the same world in headless mode:

```bash
ros2 launch ros_gz_tools world_spawner.launch.py \
  world_file:=office_environment_1.sdf \
  gui:=False
```

What this launch does:

- Starts Gazebo Sim.
- Loads the requested world.
- Configures Gazebo resource and plugin paths before Gazebo starts.
- Starts a ROS-Gazebo bridge for `/clock`.

Optional verification from another sourced terminal:

```bash
ros2 topic echo /clock --once
```

## Launch Files

### `launch/world_spawner.launch.py`

This launch file starts Gazebo Sim and a dedicated clock bridge.
It also prepares `GZ_SIM_RESOURCE_PATH` and `GZ_SIM_SYSTEM_PLUGIN_PATH` before Gazebo starts.

Launch arguments:

- `namespace`: ROS namespace applied to the bridge node started by this file.
- `world_file`: SDF file name or absolute `.sdf` path to load.
- `extra_resource_paths`: comma-separated list of directories appended to `GZ_SIM_RESOURCE_PATH`.
  Use this only when the selected world depends on meshes, models, or media that are not installed by ROS packages in
  the sourced workspace. If the world references `model://my_model`, pass the parent directory that contains the
  `my_model/` folder, not the `my_model/` folder itself.
- `gui`: `True` to start Gazebo with its GUI, `False` to run headless.
- `gui_config_file`: path to a Gazebo GUI configuration file. If empty and `gui:=True`, the package default GUI
  configuration is used.
- `autostart`: `True` to start the simulation running immediately, `False` to start paused.
- `initial_sim_time`: initial simulation time in seconds passed to Gazebo.
- `verbosity`: Gazebo verbosity level from `0` to `4`.
- `update_rate`: simulation update rate in Hz. If empty, the launch file does not pass `-z` to Gazebo.
- `respawn_bridge`: whether the clock bridge node should respawn if it exits.
- `log_level_bridge`: ROS log level used by the bridge node.

Show the launcher help:

```bash
ros2 launch ros_gz_tools world_spawner.launch.py -s
```

Example with one of the package worlds:

```bash
ros2 launch ros_gz_tools world_spawner.launch.py \
  world_file:=office_environment_1.sdf \
  gui:=True \
  autostart:=True \
  verbosity:=1
```

Example with a world stored outside the package:

```bash
ros2 launch ros_gz_tools world_spawner.launch.py \
  world_file:=/home/user/Desktop/my_world/my_world.sdf \
  extra_resource_paths:=/home/user/Desktop/my_world,/home/user/Desktop/my_world/models,/home/user/Desktop/my_world/meshes
```

The external-world example above is intentionally explicit.
Passing an absolute `world_file` is enough only when the `.sdf` file does not depend on additional external resources.
If that `.sdf` references meshes, models, or media outside the sourced ROS packages, those directories must also be
listed in `extra_resource_paths`.

Example for `model://` resolution:

- If the world contains `model://my_model`
- and the model files are stored in `/home/user/Downloads/my_model/`
- then `extra_resource_paths` should include `/home/user/Downloads`
- not `/home/user/Downloads/my_model`

### `launch/robot_spawner.launch.py`

This launch file spawns one robot entity into an already running Gazebo world.
It reads the robot description from a ROS topic and calls `ros_gz_sim/create`.
It does not start any Gazebo world and it does not start any bridge.

Launch arguments:

- `world_file`: world file used to derive the Gazebo world name.
- `topic`: ROS topic that publishes the robot description.
- `model_name`: Gazebo entity name to create.
- `allow_renaming`: whether Gazebo may rename the entity if `model_name` already exists.
- `x`, `y`, `z`: spawn position.
- `R`, `P`, `Y`: roll, pitch, and yaw in radians.

Show the launcher help:

```bash
ros2 launch ros_gz_tools robot_spawner.launch.py -s
```

Example:

```bash
ros2 launch ros_gz_tools robot_spawner.launch.py \
  world_file:=office_environment_1.sdf \
  topic:=/robot_description \
  model_name:=my_robot \
  x:=0.0 y:=0.0 z:=0.1
```

Important behavior:

- This file assumes `world name == world_file stem`.
- Example: `office_environment_1.sdf` is assumed to correspond to the Gazebo world named `office_environment_1`.
- If the running Gazebo world uses a different internal name, the spawn request will target the wrong world.

## External Worlds And Resource Resolution

There are two different cases when you launch a world:

1. `world_file` points to a world that Gazebo can already resolve.
2. `world_file` points to a world outside the package and outside the sourced ROS packages.

In case `1`, `world_file` can be something like:

- `empty.sdf`
- `office_environment_1.sdf`

In case `2`, `world_file` should be an absolute path such as:

```bash
world_file:=/home/user/Desktop/my_world/my_world.sdf
```

If that external `.sdf` references other external resources, `extra_resource_paths` must list the directories Gazebo
has to search.

Use `extra_resource_paths` only for directories that Gazebo really needs to search.
Do not add unrelated directories just because they are near the world file.

## STL Generation From Floor Plans

This package includes a small conversion pipeline that turns a black-and-white floor-plan PNG into one STL mesh.

Files involved in that workflow:

- [scripts/build_stl_from_png.sh](scripts/build_stl_from_png.sh)
- [scripts/build_stl_from_png.py](scripts/build_stl_from_png.py)

The required image convention is:

- black pixels represent obstacles or walls
- white pixels represent free space

Run the Bash wrapper like this:

```bash
./scripts/build_stl_from_png.sh <image_path> <output_path> <resolution_m_per_px> <height_m>
```

The Bash wrapper is the recommended entry point because it creates or reuses the virtual environment that the Python
script needs.

For the complete step-by-step workflow, read [scripts/README.md](scripts/README.md).

## Reproducible Environment Meshes

If a world in this package is built from a floor plan, keep the source files and the rebuild command next to the mesh.
That makes the mesh reproducible and makes it clear which source image produced which STL.

Package convention for a generated environment:

- create one folder under `meshes/` for that environment
- keep the source image files in that folder
- keep the generated STL in the same folder
- add one no-argument rebuild script in that folder with the fixed parameters used for that environment
- reference the STL from the world SDF with `package://ros_gz_tools/...`

Current example:

- rebuild script: [meshes/office_environment_1/build_office_environment_1.sh](meshes/office_environment_1/build_office_environment_1.sh)
- source image: [meshes/office_environment_1/office_environment_1.png](meshes/office_environment_1/office_environment_1.png)
- generated mesh: [meshes/office_environment_1/office_environment_1.stl](meshes/office_environment_1/office_environment_1.stl)
- consuming world: [worlds/office_environment_1.sdf](worlds/office_environment_1.sdf)

Rebuild that mesh with:

```bash
bash meshes/office_environment_1/build_office_environment_1.sh
```

## Troubleshooting

### Gazebo does not load the world

Checks:

- If the world belongs to a ROS package in the sourced workspace, confirm the file exists in that package resources.
- If the world is outside the workspace, pass its absolute path through `world_file`.
- Confirm the workspace was sourced after the last build.

### Gazebo loads the world but some resources are missing

Checks:

- Confirm the missing resources are located in directories passed through `extra_resource_paths`.
- Confirm `extra_resource_paths` uses commas, not spaces, to separate directories.
- Confirm those directories actually contain the meshes, models, or media referenced by the selected `.sdf`.

### A mesh URI inside an SDF is not resolved

Checks:

- Use `package://ros_gz_tools/...` for package-owned assets.
- Confirm the referenced file exists after the package has been built and installed.
- Print `GZ_SIM_RESOURCE_PATH` and confirm the package paths are present.

### Gazebo cannot resolve this package resources at all

Checks:

- Rebuild and source the workspace again.
- Print `GZ_SIM_RESOURCE_PATH` and confirm it contains this package `models/` and `worlds/` paths.
- Confirm the environment hook described below is installed.

### STL generation fails

Checks:

- Run the Bash wrapper, not only the Python script, so the virtual environment is created if needed.
- Confirm the input image uses black walls and white free space.
- Review the full workflow in [scripts/README.md](scripts/README.md).

## Colcon Hook For Gazebo Resource Paths

Gazebo resolves package worlds, models, and media through `GZ_SIM_RESOURCE_PATH`.
This package installs a colcon environment hook so the package resource directories are registered automatically after
the workspace is sourced.

That hook is defined in [hooks/ros_gz_tools.dsv.in](hooks/ros_gz_tools.dsv.in):

```bash
prepend-non-duplicate;GZ_SIM_RESOURCE_PATH;@CMAKE_INSTALL_PREFIX@/share/@PROJECT_NAME@/models
prepend-non-duplicate;GZ_SIM_RESOURCE_PATH;@CMAKE_INSTALL_PREFIX@/share/@PROJECT_NAME@/worlds
```

What those entries do:

- `prepend-non-duplicate` adds the path only if it is not already present.
- `@CMAKE_INSTALL_PREFIX@` expands to the package install prefix.
- `@PROJECT_NAME@` expands to `ros_gz_tools`.

The hook is installed from [CMakeLists.txt](CMakeLists.txt) with:

```cmake
ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")
```

If you build with `--merge-install`, the installed package resources are typically:

```text
install/share/ros_gz_tools/models
install/share/ros_gz_tools/worlds
```

If you build without `--merge-install`, the installed package resources are typically:

```text
install/ros_gz_tools/share/ros_gz_tools/models
install/ros_gz_tools/share/ros_gz_tools/worlds
```

In both cases, sourcing the workspace should make those paths visible to Gazebo through `GZ_SIM_RESOURCE_PATH`.
