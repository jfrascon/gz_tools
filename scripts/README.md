# From 2D floor plan (PDF/PNG) to STL and Gazebo SDF in ROS2

## Phase 1: Vectorize and simplify walls

1. Open the floor-plan PDF in Inkscape.
2. Create a new layer and name it "Walls".
3. Select the "Draw Bezier curves" tool (pen).
4. Draw straight lines over the main walls in the floor plan.
5. Select all the lines you drew.
6. Set the stroke color to pure black (`#000000`).
7. Adjust stroke width so it matches the real wall width and keep it consistent across the whole plan. Avoid very thin strokes so they do not break when exporting to PNG.
8. Open the "Fill and Stroke" panel and go to the "Stroke style" tab.
9. Set caps to straight (`butt`) and joins to straight (`miter`). Avoid rounded styles to keep corners clean and geometrically stable.
10. Leave white gaps where doors are. The robot will pass through those openings.
11. Select all black strokes.
12. In the top menu, click **Path > Stroke to Path**. This converts simple lines into closed wall shapes.
13. Without deselecting, click **Path > Union**. Then verify the result is one clean geometry: no loose pieces ("islands"), no self-intersections, and no micro-gaps between walls. This check prevents the STL generator from discarding invalid polygons.

## Phase 2: Export the drawing to PNG

Goal of this phase: export a clean image where walls are black and free space is white.
This is the format expected by the STL conversion script.

1. Hide the original PDF layer. Only your wall drawing should be visible.
2. Verify walls are pure black (`#000000`).
3. Select the wall drawing.
4. Open the export panel with **File > Export**.
5. Choose the **Selection** tab.
6. Set **300** in the **DPI** field.
7. In the export panel, set **Background** to pure white with 100% opacity (`ffffffff`).
8. Click "Export" and save the image with any name you want.

## Phase 3: Compute the scale

Goal of this phase: compute resolution in meters per pixel (`m/px`) so the 2D plan is converted at real scale in 3D.

1. Get the real-world distance in meters of one wall in your modeled environment, preferably a long wall.
2. In the exported PNG, measure how many pixels that same wall occupies.
3. Compute resolution with this formula: `resolution = meters / pixels`.
4. Example: if the wall is `19.40 m` and occupies `1542 px`, then `19.40 / 1542 = 0.01258 m/px`.
5. The longer the wall used for the measurement, the lower the relative resolution error tends to be.
6. Save this value: it is the value you must pass to the script as the resolution parameter.

## Phase 4: Run the scripts to generate the STL

Goal of this phase: generate the final STL at the correct scale from the PNG image and computed resolution.

1. Place these scripts in the same folder: `build_stl_from_png.sh` and `build_stl_from_png.py`, together with your PNG image.
2. Open a terminal in that folder.
3. Give execution permissions to the Bash script:
`chmod +x build_stl_from_png.sh`
4. Run the script with positional parameters:
`./build_stl_from_png.sh <image.png> <output.stl> <resolution_m_per_pixel> <height_m>`
5. Real example:
`./build_stl_from_png.sh planta.png planta.stl 0.01258 2.5`
6. The script creates/reuses a virtual environment in `/tmp/build_stl_from_png`, installs dependencies, and runs the conversion.
7. If everything is correct, the STL appears at the output path you provided.

## Phase 5: Review and adjust the STL coordinate system

Goal of this phase: understand the generated STL orientation and place its frame in a more convenient convention for simulation.

1. The STL is generated following image-coordinate conventions:
   `X` increases to the right, `Y` increases downward, and `Z` is perpendicular to the image plane (right-hand rule).
2. This convention is normal in image processing because it is based on pixel indexing (row/column).
3. For 3D simulation, it is usually more practical to use `Z` pointing upward.
4. MeshLab is recommended to reorient the STL.
5. To flip orientation and make `Z` point upward, rotate the STL **180 degrees around the X axis**.
   In MeshLab: **Filters > Normals, Curvatures and Orientation > Transform: Rotate, Translate, Center**, then set `Axis = X` and `Angle = 180°`.
6. After rotation, you can translate the STL in `X`, `Y`, and `Z` as needed to place the model frame.
7. Practical recommendation: place the frame at the center of the model's bottom face.
   In MeshLab: **Filters > Normals, Curvatures and Orientation > Transform: Rotate, Translate, Center**. Center the model in `X` and `Y`, then adjust `Z` translation so the base lies at `Z = 0`.
8. Using adjustments from steps 5 and 7, the coordinate ranges become:
   `X` in `[-X_max/2, X_max/2]`, `Y` in `[-Y_max/2, Y_max/2]`, and `Z` in `[0, Z_max]`.

## Phase 6: Use the STL in Gazebo

Goal of this phase: reference the STL inside an SDF world using ROS 2 package paths (`package://`).

1. Place the STL inside the package, for example at:
   `gz_tools/meshes/office_environment_1/office_environment_1.stl`.
2. Open the SDF world where you want to use the environment. Real example:
   `gz_tools/worlds/office_environment_1.sdf`.
3. Add a static model with both `visual` and `collision` using the same mesh.
4. Use package URIs (not `file://`) so it works correctly in ROS 2:

   ```xml
   <model name="office_environment_1">
     <static>true</static>
     <link name="link">
       <visual name="visual">
         <geometry>
           <mesh>
             <uri>package://gz_tools/meshes/office_environment_1/office_environment_1.stl</uri>
           </mesh>
         </geometry>
       </visual>
       <collision name="collision">
         <geometry>
           <mesh>
             <uri>package://gz_tools/meshes/office_environment_1/office_environment_1.stl</uri>
           </mesh>
         </geometry>
       </collision>
     </link>
     <pose>0 0 0 0 0 0</pose>
   </model>
   ```

5. Save the `.sdf`.
6. Launch the world and verify the environment appears with correct visualization and collisions.
