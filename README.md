Explicar los hooks
https://robotics.stackexchange.com/questions/113171/how-to-include-a-local-model-into-gz-sim-harmonic-from-a-world-sdf

## Colcon hooks to automatically register Gazebo resources

Gazebo Sim discovers models, media, and world files via the environment variable `GZ_SIM_RESOURCE_PATH`.

Colcon hooks are scripts or files that are automatically installed and sourced by the ROS2 build system (colcon) when a
package is built. They allow a package to extend or modify the environment of the workspace when the file `setup.bash`
(or `setup.zsh`, etc.) in the `install` directory of the workspace is sourced.

By using a colcon hook the enviroment variable `GZ_SIM_RESOURCE_PATH` is automatically set to include the paths to your
models, media, and world files when you source your workspace, `source <your_workspace>/install/setup.bash`.

There are two types of hooks:

1. **Declarative hooks**: These are files that define environment variables and their values. They are typically named
with a `.dsv.in` extension.

```bash
prepend-non-duplicate;GZ_SIM_RESOURCE_PATH;@CMAKE_INSTALL_PREFIX@/share/@PROJECT_NAME@/models
prepend-non-duplicate;GZ_SIM_RESOURCE_PATH;@CMAKE_INSTALL_PREFIX@/share/@PROJECT_NAME@/worlds
```

**prepend-non-duplicate**: ensures the path is prepended only once to avoid duplicates.
**@CMAKE_INSTALL_PREFIX@**: expands to the install prefix of the package.
**@PROJECT_NAME@**: expands to the package name (e.g., eut_gz_models).

When you compile using the flag `--merge-install`, all packages are installed into a common installation tree, the
`install` directory of the workspace.

```bash
install/
├── setup.bash
├── share/
│   ├── eut_gz_models/
│   │   ├── models/
│   │   └── worlds/
│   └── another_package/
```

In the environment hooks, `@MAKE_INSTALL_PREFIX@` resolves to `install/`, and the resources are located at:

```bash
install/share/eut_gz_models/models
install/share/eut_gz_models/worlds
```

The environment variable `GZ_SIM_RESOURCE_PATH` is populated:

```bash
GZ_SIM_RESOURCE_PATH="<workspace_path>/install/share/eut_gz_models/models:<workspace_path>/install/share/eut_gz_models/worlds:<other_paths>
```

When you compile without using the flag `--merge-install`, each package is installed into its own subdirectory.

```bash
install/
├── eut_gz_models/
│   ├── setup.bash
│   └── share/
│       └── eut_gz_models/
│           ├── models/
│           └── worlds/
├── another_package/
```

In the environment hooks, `@MAKE_INSTALL_PREFIX@` resolves to `install/eut_gz_models`, and the resources are located
at:

```bash
install/eut_gz_models/share/eut_gz_models/models
install/eut_gz_models/share/eut_gz_models/worlds
```

The environment variable `GZ_SIM_RESOURCE_PATH` is populated:

```bash
GZ_SIM_RESOURCE_PATH="<workspace_path>/install/eut_gz_models/share/eut_gz_models/models:<workspace_path>/install/eut_gz_models/share/eut_gz_models/worlds:<other_paths>
```

So with the same lines 2 lines in your hook the environment variable `GZ_SIM_RESOURCE_PATH` is populated correctly.

You also have to add the following line to your `CMakeLists.txt` in order to install the environment hook:

```cmake
ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")
```

To test that the hook is working as expected, try:

```bash
cd <workspace_path>
colcon build --merge-install --symlink-install --parallel-workers 6 --mixin release --mixin compile-commands --cmake-args -DCMAKE_CXX_FLAGS=-Wall\ -Wextra\ -Wpedantic\ -Wnon-virtual-dtor\ -Woverloaded-virtual\ -Wnull-dereference\ -Wunused-parameter
source install/setup.bash
echo ${GZ_SIM_RESOURCE_PATH}
gz sim factory_w_pallets.sdf
```

References:
- [How to <include> a local model into GZ-Sim Harmonic from a world.sdf?](https://robotics.stackexchange.com/questions/113171/how-to-include-a-local-model-into-gz-sim-harmonic-from-a-world-sdf)
- [ros_gz_project_template](https://github.com/gazebosim/ros_gz_project_template/tree/main/ros_gz_example_description)