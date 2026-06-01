cmake_minimum_required(VERSION 3.22.1)

project(agimus_demos_common_kuka LANGUAGES CXX)

find_package(ament_cmake_auto REQUIRED)
ament_auto_find_build_dependencies()

ament_python_install_package(agimus_demos_common_kuka SCRIPTS_DESTINATION
                             lib/agimus_demos_common_kuka)

install(DIRECTORY config launch rviz DESTINATION share/agimus_demos_common_kuka)

ament_auto_package()
