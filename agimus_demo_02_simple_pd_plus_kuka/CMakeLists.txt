cmake_minimum_required(VERSION 3.22.1)

project(agimus_demo_02_simple_pd_plus_kuka LANGUAGES CXX)

find_package(ament_cmake_auto REQUIRED)
ament_auto_find_build_dependencies()

ament_auto_package(INSTALL_TO_SHARE launch config)
