from launch import LaunchContext, LaunchDescription
from launch.actions import (
    OpaqueFunction,
    RegisterEventHandler,
    TimerAction,
)

from launch.event_handlers import OnProcessStart
from launch.launch_description_entity import LaunchDescriptionEntity
from launch_ros.actions import Node

import agimus_demos_common_kuka.launch_nodes as nodes
from agimus_demos_common_kuka.launch_utils_kuka import (
    generate_default_kuka_args,
    generate_cardboard_detector_camera_args,
    generate_mpc_args,
    get_use_sim_time,
    path_join,
    include_path_join,
    required_node,
    parameter_value_xacro,
    SetupContext,
)

from agimus_demos_common.static_transform_publisher_node import (
    static_transform_publisher_node,
)

PKG = "agimus_demo_16_cardboard_insert_kuka"


def launch_setup(
        context: LaunchContext, *_args, **_kwargs
) -> list[LaunchDescriptionEntity]:
    ctx = SetupContext(context, PKG)

    # prepare the robot
    kuka_robot_launch = include_path_join(
        "launch", "kuka", "kuka_common_lfc.launch.py")

    # do not launch the rest if we are on the aux launch
    if ctx.config_bool("on_aux"):
        return [kuka_robot_launch]

    robot_name = ctx.config("robot_name")
    use_mpc_debugger = ctx.config("use_mpc_debugger")
    agimus_controller_yaml = ctx.config_path("config", "controller_config_file")
    ocp_definition_file = ctx.config_path("config", "ocp_definition_file")

    agimus_controller_node = nodes.agimus_controller(
        robot_name, agimus_controller_yaml, ocp_definition_file)

    trajectory_goal_server_node = nodes.trajectory_goal_server(robot_name)

    obstacles_config_path = ctx.config_path("urdf", "obstacles_config_file")
    environment_description = parameter_value_xacro(obstacles_config_path)

    environment_publisher_node = nodes.environment_publisher(
        robot_name, environment_description)

    tf_node = static_transform_publisher_node(
        frame_id=f"{robot_name}_link_0",
        child_frame_id="obstacle1",
    )

    mpc_debugger = nodes.mpc_debugger(robot_name, use_mpc_debugger)

    launch = [
        kuka_robot_launch,
        agimus_controller_node,
        environment_publisher_node,
        tf_node,
        *required_node(mpc_debugger),
        RegisterEventHandler(
            event_handler=OnProcessStart(
                target_action=agimus_controller_node,
                on_start=TimerAction(
                    period=2.0,
                    actions=[trajectory_goal_server_node],
                ),
            )
        ),
        required_node(trajectory_goal_server_node)[1],
    ]

    # prepare the camera and the detector
    camera_embedded = ctx.config_bool("camera_embedded")
    detector_file = ctx.config_path("detector")
    calib_file = ctx.config_path("calib_cam")
    robot_calib_file = ctx.config_path("calib_robot")
    if ctx.config("template") == 'none':
        template_file = None
        mode = 'parts'
    else:
        template_file = ctx.config_path("template")
        mode = 'full'

    sample_file = ctx.config_path_optional("simulate")
    hole_planner_yaml = path_join("config", "hole_planner.yaml", pkg=PKG)

    if not camera_embedded:
        camera_node = nodes.camera(detector_file, calib_file, sample_file)

        launch += [*required_node(camera_node)]
        sample_file = None

    detector_node = nodes.detector(
        detector_file, template_file,
        calib_file=calib_file,
        robot_calib_file=robot_calib_file,
        simulate_file=sample_file,
        camera_embedded=camera_embedded,
        detect_holder=True,
        debug=False)

    launch += [*required_node(detector_node)]

    planner = Node(
        package="agimus_cardboard",
        executable="hole_insert_planner",
        parameters=[get_use_sim_time(), hole_planner_yaml],
        output="screen",
        arguments=["--robot_name", robot_name,
                   "--mode", mode,
                   #"--ros-args", "--log-level",
                   #"hole_insert_planner:=debug",
                   ],
    )

    launch += [*required_node(planner)]

    return launch


def generate_launch_description():
    return LaunchDescription(
        generate_default_kuka_args()
        + generate_cardboard_detector_camera_args()
        + generate_mpc_args()
        + [OpaqueFunction(function=launch_setup)]
    )
