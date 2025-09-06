cmake_minimum_required(VERSION 3.8)
project(eut_gz_models)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch models worlds DESTINATION share/${PROJECT_NAME})

ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")

if(BUILD_TESTING)
    find_package(ament_lint_auto REQUIRED)
    ament_lint_auto_find_test_dependencies()
endif()

ament_package()