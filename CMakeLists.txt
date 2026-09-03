cmake_minimum_required(VERSION 3.8)
project(ros_gz_tools)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(DIRECTORY config meshes models worlds DESTINATION share/${PROJECT_NAME})
install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
  PATTERN "__pycache__" EXCLUDE
  PATTERN "*.pyc" EXCLUDE)

install(FILES README.md LICENSE DESTINATION share/${PROJECT_NAME})

install(PROGRAMS
  scripts/wait_for_gz_service.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_environment_hooks(
  "${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")

if(BUILD_TESTING)
  find_package(ament_cmake_flake8 REQUIRED)
  find_package(ament_cmake_pytest REQUIRED)
  find_package(ament_lint_auto REQUIRED)

  ament_add_pytest_test(test_build_stl_from_png test/test_build_stl_from_png.py)
  ament_add_pytest_test(test_helpers test/test_helpers.py)
  ament_add_pytest_test(test_launch_contract test/test_launch_contract.py)
  ament_add_pytest_test(test_resources test/test_resources.py)
  ament_add_pytest_test(test_wait_for_gz_service test/test_wait_for_gz_service.py)

  # ament_lint_auto cannot pass this package's 100-character and E203 settings to Flake8.
  # Exclude the automatic test and register Flake8 once with the shared package configuration.
  list(APPEND AMENT_LINT_AUTO_EXCLUDE
    ament_cmake_flake8)
  ament_flake8(CONFIG_FILE "${CMAKE_CURRENT_SOURCE_DIR}/ament_flake8.ini")

  # Register the remaining linters declared as test dependencies in package.xml.
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
