cmake_minimum_required(VERSION 3.8)
project(ros_gz_tools)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch meshes models scripts worlds DESTINATION share/${PROJECT_NAME})

install(
    PROGRAMS
        scripts/build_stl_from_png.sh
        scripts/build_stl_from_png.py
        meshes/office_environment_1/build_office_environment_1.sh
    DESTINATION lib/${PROJECT_NAME}
)

ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")

if(BUILD_TESTING)
    find_package(ament_lint_auto REQUIRED)
    ament_lint_auto_find_test_dependencies()
endif()

ament_package()
