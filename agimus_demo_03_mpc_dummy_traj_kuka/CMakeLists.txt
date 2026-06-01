cmake_minimum_required(VERSION 3.22.1)

project(agimus_demo_03_mpc_dummy_traj_kuka LANGUAGES CXX)

find_package(ament_cmake_auto REQUIRED)
ament_auto_find_build_dependencies()

ament_auto_package(INSTALL_TO_SHARE launch config urdf)
