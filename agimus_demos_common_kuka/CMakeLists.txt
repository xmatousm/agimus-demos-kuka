cmake_minimum_required(VERSION 3.22.1)

project(agimus_demos_common_kuka LANGUAGES CXX)

find_package(ament_cmake_auto REQUIRED)
ament_auto_find_build_dependencies()

# Note: we are merging modules into agimus_demos_common package
ament_python_install_package(agimus_demos_common SCRIPTS_DESTINATION
                             lib/agimus_demos_common)

install(DIRECTORY config launch rviz DESTINATION share/agimus_demos_common)

ament_auto_package()
