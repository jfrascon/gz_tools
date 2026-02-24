# gz_tools

`gz_tools` is a ROS 2 package for Gazebo Sim resources and utilities.
It provides worlds, models, meshes, launch files, and helper scripts.
It is designed to run simulation scenarios quickly and to maintain environments generated from floor plans.

## What this package includes

This package includes these resource categories:

- `worlds/`: SDF world files for Gazebo Sim.
- `models/`: Gazebo model directories (`model.config`, `model.sdf`, meshes, thumbnails).
- `meshes/`: custom mesh assets and source files.
- `launch/`: ROS 2 launch files to run worlds and spawn robots.
- `scripts/`: utility scripts, including PNG floor plan to STL conversion.
- `config/`: Gazebo GUI configuration.
- `hooks/`: environment hook templates for Gazebo resource paths.

## Prerequisites

Before using this package, confirm your environment includes a ROS 2 installation with Gazebo Sim integration: `ros_gz_sim` and `ros_gz_bridge` available in the sourced environment.

## Quickstart

Build and source your workspace:

```bash
cd <workspace_path>
colcon build --merge-install --symlink-install
source install/setup.bash
```

Launch Gazebo with the office world:

```bash
ros2 launch gz_tools gz_world_spawner.launch.py world_file:=office_environment_1.sdf gui:=True
```

Run headless (no GUI):

```bash
ros2 launch gz_tools gz_world_spawner.launch.py world_file:=office_environment_1.sdf gui:=False
```

Expected result:

- Gazebo starts and loads `office_environment_1.sdf`.
- The office mesh appears in the scene.
- The world runs with the clock bridge started by the launcher.

Optional check from another sourced terminal:

```bash
ros2 topic echo /clock --once
```

## Launch usage

### World launcher

The purpose of the script [launch/gz_world_spawner.launch.py](launch/gz_world_spawner.launch.py) is:

- Starts Gazebo Sim.
- Sets Gazebo resource and plugin paths.
- Starts a ROS-Gazebo clock bridge.

Launch arguments:

- `namespace`: optional ROS namespace.
- `world_file`: SDF file name to load (example: `office_environment_1.sdf`).
- `gui`: `True` or `False`.
- `gui_config_file`: optional GUI config file path.
- `autostart`: start simulation running (`True`) or paused (`False`).
- `initial_sim_time`: initial simulation time in seconds.
- `verbosity`: Gazebo verbosity level (`0` to `4`).
- `update_rate`: optional simulation update rate in Hz.
- `respawn_rosgz_bridge`: whether to respawn the `rosgz_bridge_node` if it dies.
- `log_level_rosgz_bridge`: log level for the `rosgz_bridge_node`.

For full details from the launcher itself, run:

```bash
ros2 launch gz_tools gz_world_spawner.launch.py -s
```

Example:

```bash
ros2 launch gz_tools gz_world_spawner.launch.py \
  world_file:=office_environment_1.sdf \
  gui:=True \
  autostart:=True \
  verbosity:=1
```

Current launcher logic assumes `world name == world file name without .sdf`.

### Robot spawner

The purpose of the script [launch/gz_robot_spawner.launch.py](launch/gz_robot_spawner.launch.py) is:

- Spawns a robot model into a running Gazebo world from a ROS topic.

Launch arguments:

- `world_file`: world file name used to derive world name.
- `topic`: ROS topic carrying the robot description.
- `model_name`: entity name in Gazebo.
- `allow_renaming`: whether Gazebo can rename on name collision.
- `x`, `y`, `z`: spawn position.
- `R`, `P`, `Y`: roll, pitch, and yaw.

For full details from the launcher itself, run:

```bash
ros2 launch gz_tools gz_robot_spawner.launch.py -s
```

Example:

```bash
ros2 launch gz_tools gz_robot_spawner.launch.py \
  world_file:=office_environment_1.sdf \
  topic:=/robot_description \
  model_name:=my_robot \
  x:=0.0 y:=0.0 z:=0.1
```

## Generate STL from a floor plan

This package includes utilities to convert a 2D floor plan image into a 3D STL wall mesh.
This follows a workflow style commonly used in Gazebo Classic projects.

The conversion scripts are:

- [scripts/build_stl_from_png.sh](scripts/build_stl_from_png.sh) and
- [scripts/build_stl_from_png.py](scripts/build_stl_from_png.py).

Use the Bash wrapper as:

```bash
./scripts/build_stl_from_png.sh <image_path> <output_path> <resolution_m_per_px> <height_m>
```

Image convention expected by the conversion pipeline:

- black pixels = obstacles/walls
- white pixels = free space

For the full step-by-step process (from PDF/PNG editing to SDF integration), read [scripts/README.md](scripts/README.md).

## Office environment reproducibility

If you create worlds by raising walls from a floor plan, follow this package convention.
Using one convention makes regeneration repeatable and avoids broken mesh references.

Convention to follow for each environment:

- Create one folder under `meshes/` for the environment (example: `meshes/office_environment_1/`).
- Keep floor-plan sources in that folder (`.png`, optional `.svg`, etc.).
- Keep the generated STL in the same folder, using the environment name.
- Add one rebuild script in that folder with no arguments and fixed parameters.
- In the world SDF, reference the STL with a `package://gz_tools/...` URI.

Example in this package:

- Rebuild script: [meshes/office_environment_1/build_office_environment_1.sh](meshes/office_environment_1/build_office_environment_1.sh).
- Input plan: [meshes/office_environment_1/office_environment_1.png](meshes/office_environment_1/office_environment_1.png).
- Output mesh: [meshes/office_environment_1/office_environment_1.stl](meshes/office_environment_1/office_environment_1.stl).
- World file: [worlds/office_environment_1.sdf](worlds/office_environment_1.sdf).

Run the rebuild script:

```bash
bash meshes/office_environment_1/build_office_environment_1.sh
```

This script:

- Uses `office_environment_1.png` as input.
- Calls [scripts/build_stl_from_png.sh](scripts/build_stl_from_png.sh) with fixed resolution and wall height.
- Regenerates `office_environment_1.stl` in the same environment folder.

## Troubleshooting

### World file not found

Symptoms:

- Gazebo does not load the world.

Checks:

- Confirm the world exists under `worlds/`.
- Use only the file name in the launch argument (example: `world_file:=office_environment_1.sdf`).
- Confirm workspace is sourced: `source install/setup.bash`.

### Mesh URI not found in SDF

Symptoms:

- The world loads but the model mesh is missing.

Checks:

- Use `package://gz_tools/...` URIs in SDF.
- Confirm the mesh file exists in the package share path after build.
- Confirm `GZ_SIM_RESOURCE_PATH` includes package resources.

### Resource paths are missing

Symptoms:

- Gazebo cannot resolve worlds or models from this package.

Checks:

- `echo ${GZ_SIM_RESOURCE_PATH}`
- Rebuild and source the workspace again.
- Ensure the environment hook is installed (see hook section below).

### STL generation fails

Symptoms:

- Script exits with dependency or geometry errors.

Checks:

- Run the Bash wrapper script (it manages venv and dependencies).
- Validate the input image convention: black obstacles, white free space.
- Review the full generation guide in [scripts/README.md](scripts/README.md).

## Colcon hooks to automatically register Gazebo resources

Gazebo Sim resolves models, media, and world files through `GZ_SIM_RESOURCE_PATH`.
This package uses a colcon hook so that, after building and sourcing the workspace, Gazebo can find `models/` and
`worlds/` from this package without manual `export` commands.

In this package, that behavior is defined in [hooks/gz_tools.dsv.in](hooks/gz_tools.dsv.in).
The hook is declarative (`.dsv.in`) and prepends package paths without duplicates:

```bash
prepend-non-duplicate;GZ_SIM_RESOURCE_PATH;@CMAKE_INSTALL_PREFIX@/share/@PROJECT_NAME@/models
prepend-non-duplicate;GZ_SIM_RESOURCE_PATH;@CMAKE_INSTALL_PREFIX@/share/@PROJECT_NAME@/worlds
```

`prepend-non-duplicate` avoids repeated entries.
`@CMAKE_INSTALL_PREFIX@` expands to the package install prefix.
`@PROJECT_NAME@` expands to `gz_tools`.
The hook is installed from [CMakeLists.txt](CMakeLists.txt) with:

```cmake
ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")
```

To verify that everything is working, build and source the workspace, print the variable, and launch a world:

```bash
cd <workspace_path>
colcon build --merge-install --symlink-install --parallel-workers 6 --mixin release --mixin compile-commands --cmake-args -DCMAKE_CXX_FLAGS=-Wall\ -Wextra\ -Wpedantic\ -Wnon-virtual-dtor\ -Woverloaded-virtual\ -Wnull-dereference\ -Wunused-parameter
source install/setup.bash
echo ${GZ_SIM_RESOURCE_PATH}
gz sim factory_w_pallets.sdf
```

If you build with `--merge-install`, all packages share `install/` and the resolved package resources are:

```bash
install/
├── setup.bash
├── share/
│   ├── gz_tools/
│   │   ├── models/
│   │   └── worlds/
│   └── another_package/
```

`@CMAKE_INSTALL_PREFIX@` resolves to `install/`, so package resources are:

```bash
install/share/gz_tools/models
install/share/gz_tools/worlds
```

and `GZ_SIM_RESOURCE_PATH` includes:

```bash
GZ_SIM_RESOURCE_PATH="<workspace_path>/install/share/gz_tools/models:<workspace_path>/install/share/gz_tools/worlds:<other_paths>
```

If you build without `--merge-install`, each package gets its own install prefix:

```bash
install/
├── gz_tools/
│   ├── setup.bash
│   └── share/
│       └── gz_tools/
│           ├── models/
│           └── worlds/
├── another_package/
```

`@CMAKE_INSTALL_PREFIX@` resolves to `install/gz_tools`, so package resources are:

```bash
install/gz_tools/share/gz_tools/models
install/gz_tools/share/gz_tools/worlds
```

and `GZ_SIM_RESOURCE_PATH` includes:

```bash
GZ_SIM_RESOURCE_PATH="<workspace_path>/install/gz_tools/share/gz_tools/models:<workspace_path>/install/gz_tools/share/gz_tools/worlds:<other_paths>
```

References:

- [How to include a local model into GZ-Sim Harmonic from a world.sdf?](https://robotics.stackexchange.com/questions/113171/how-to-include-a-local-model-into-gz-sim-harmonic-from-a-world-sdf)
- [ros_gz_project_template](https://github.com/gazebosim/ros_gz_project_template/tree/main/ros_gz_example_description)
