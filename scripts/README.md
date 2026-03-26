# Floor Plan To STL Workflow

This document explains the workflow used in this package to convert a 2D floor plan into one STL mesh that can be
referenced from a Gazebo world.

The conversion pipeline expects one specific image convention:

- black pixels represent walls or obstacles
- white pixels represent free space

If the exported image does not follow that convention, the generated STL will not represent the intended geometry.

## Phase 1: Trace The Walls In Inkscape

Goal of this phase:
create one clean 2D wall geometry that can later be exported as a black-and-white PNG.

1. Open the floor-plan PDF in Inkscape.
2. Create a new layer named `Walls`.
3. Select the Bezier or pen tool.
4. Draw the wall centerlines or wall outlines that you want to keep in simulation.
5. Select all the new wall strokes.
6. Set the stroke color to pure black, `#000000`.
7. Adjust the stroke width so it matches the real wall thickness and keep that width consistent across the plan.
8. In **Fill and Stroke > Stroke style**, set caps to `butt` and joins to `miter`.
9. Leave white gaps where doors or other openings must remain traversable.
10. Convert the strokes into filled wall polygons with **Path > Stroke to Path**.
11. Merge all wall polygons with **Path > Union**.
12. Inspect the result and remove loose islands, self-intersections, and tiny gaps.

The important output of this phase is one clean vector geometry that represents only the walls you want to extrude.

## Phase 2: Export The PNG Used By The Generator

Goal of this phase:
export one raster image where the wall geometry is black and the background is white.

1. Hide the original PDF layer.
2. Leave visible only the wall geometry prepared in Phase 1.
3. Verify again that the walls are pure black.
4. Open **File > Export**.
5. Export the selection, not the full page.
6. Set the export DPI to `300`.
7. Set the background color to opaque white, `ffffffff`.
8. Export the PNG.

The important output of this phase is one PNG where black means wall and white means free space.

## Phase 3: Compute The Resolution

Goal of this phase:
compute the real-world scale used to convert pixels into meters.

1. Pick one wall whose real length is known in meters.
2. Measure the same wall in the exported PNG, in pixels.
3. Compute:

   ```text
   resolution_m_per_px = wall_length_m / wall_length_px
   ```

4. Example:

   ```text
   19.40 m / 1542 px = 0.01258 m/px
   ```

Use the longest reliable wall you have. Longer measurements reduce the relative scaling error.

## Phase 4: Generate The STL

Goal of this phase:
extrude the black wall polygons into one STL mesh at the correct real-world scale.

Required files:

- `build_stl_from_png.sh`
- `build_stl_from_png.py`
- the PNG exported in Phase 2

Recommended command:

```bash
./build_stl_from_png.sh <image.png> <output.stl> <resolution_m_per_px> <height_m>
```

Real example:

```bash
./build_stl_from_png.sh planta.png planta.stl 0.01258 2.5
```

What the Bash wrapper does:

- creates or reuses a virtual environment in `/tmp/build_stl_from_png`
- installs the Python dependencies needed by the generator
- runs the Python generator with the provided inputs

If the command succeeds, the requested STL file is written at `output.stl`.

## Phase 5: Reorient The STL For Simulation

Goal of this phase:
move from image coordinates to a mesh frame that is easier to use in Gazebo.

The raw STL follows the image convention used during extrusion:

- `X` increases to the right
- `Y` increases downward
- `Z` is perpendicular to the image plane

That convention is normal for image processing, but it is usually not the most convenient frame for simulation.

Recommended workflow in MeshLab:

1. Open the STL.
2. Rotate the mesh `180` degrees around the `X` axis.
3. Translate the mesh so the model frame is where you want it.

One practical convention is:

- center the model in `X`
- center the model in `Y`
- place the floor-contact face at `Z = 0`

That convention makes the STL easier to reuse as a static environment mesh in Gazebo.

## Phase 6: Reference The STL From An SDF World

Goal of this phase:
use the generated STL from a Gazebo world that belongs to this ROS package.

1. Place the STL under this package, for example:

   ```text
   ros_gz_tools/meshes/office_environment_1/office_environment_1.stl
   ```

2. Open the target world SDF, for example:

   ```text
   ros_gz_tools/worlds/office_environment_1.sdf
   ```

3. Add a static model that uses the STL in both the `visual` block and the `collision` block.
4. Reference the STL with a `package://ros_gz_tools/...` URI, not `file://`.

Example:

```xml
<model name="office_environment_1">
  <static>true</static>
  <link name="link">
    <visual name="visual">
      <geometry>
        <mesh>
          <uri>package://ros_gz_tools/meshes/office_environment_1/office_environment_1.stl</uri>
        </mesh>
      </geometry>
    </visual>
    <collision name="collision">
      <geometry>
        <mesh>
          <uri>package://ros_gz_tools/meshes/office_environment_1/office_environment_1.stl</uri>
        </mesh>
      </geometry>
    </collision>
  </link>
  <pose>0 0 0 0 0 0</pose>
</model>
```

Using the same mesh in both blocks means:

- Gazebo renders the same geometry that it uses for collisions
- the visual world and the collision world stay aligned
