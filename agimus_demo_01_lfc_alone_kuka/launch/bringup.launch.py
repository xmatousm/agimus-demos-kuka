from launch import LaunchContext, LaunchDescription
from launch.actions import OpaqueFunction
from launch.launch_description_entity import LaunchDescriptionEntity

from agimus_demos_common_kuka.launch_utils_kuka import include_path_join


def launch_setup(
        _context: LaunchContext, *_args, **_kwargs
) -> list[LaunchDescriptionEntity]:
    return [include_path_join("launch", "kuka", "kuka_common_lfc.launch.py")]


def generate_launch_description():
    return LaunchDescription([OpaqueFunction(function=launch_setup)])
