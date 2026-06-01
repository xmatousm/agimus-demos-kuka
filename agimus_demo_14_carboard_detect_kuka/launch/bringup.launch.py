from launch import LaunchContext, LaunchDescription
from launch.actions import OpaqueFunction
from launch.launch_description_entity import LaunchDescriptionEntity

from agimus_demos_common_kuka.launch_utils_kuka import (
    generate_default_kuka_args,
    generate_cardboard_detector_camera_args,
    required_node,
    SetupContext,
)

import agimus_demos_common_kuka.launch_nodes as nodes

PKG = "agimus_demo_14_cardboard_detect_kuka"


def launch_setup(
        context: LaunchContext, *_args, **_kwargs
) -> list[LaunchDescriptionEntity]:
    ctx = SetupContext(context, PKG)

    camera_embedded = ctx.config_bool("camera_embedded")
    detector_file = ctx.config_path("detector")
    calib_file = ctx.config_path("calib_cam")
    robot_calib_file = ctx.config_path("calib_robot")

    template_file = ctx.config_path("template")
    sample_file = ctx.config_path_optional("simulate")
    mask_file = ctx.config_path_optional("mask")

    launch = []

    if not camera_embedded:
        camera_node = nodes.camera(
            detector_file, calib_file, sample_file, mask_file, debug=True)

        launch += [*required_node(camera_node)]
        sample_file = None
        mask_file = None

    detector_node = nodes.detector(
        detector_file, template_file,
        calib_file=calib_file,
        simulate_file=sample_file,
        mask_file=mask_file,
        debug=True,
        robot_calib_file=robot_calib_file,
        camera_embedded=camera_embedded)

    launch += [*required_node(detector_node)]

    return launch


def generate_launch_description():
    return LaunchDescription(
        generate_default_kuka_args()
        + generate_cardboard_detector_camera_args()
        + [OpaqueFunction(function=launch_setup)]
    )
