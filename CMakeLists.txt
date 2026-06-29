cmake_minimum_required(VERSION 3.8)
project(ros_gz_tools)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config meshes models worlds DESTINATION share/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})

install(PROGRAMS
  scripts/delete_gz_entity
  scripts/spawn_gz_entity
  scripts/wait_for_gz_service.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_environment_hooks(
  "${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
