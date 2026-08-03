import ast
from copy import deepcopy

from launch import LaunchContext, LaunchDescription
from launch.actions import (
    ExecuteProcess,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_entity import LaunchDescriptionEntity
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from controller_manager.launch_utils import (
    generate_controllers_spawner_launch_description,  # noqa: I001
)

from papouch_ros.launch_helpers import quido_node, schunk_gripper_node

from agimus_demos_common_kuka.launch_utils_kuka import (
    generate_default_kuka_args,
    get_use_sim_time,
    parameter_value_xacro,
    path_join,
    include_path_join,
    SetupContext,
    required_node,
    remap_to_ns,
)

import launch.logging


def launch_setup(
        context: LaunchContext, *_args, **_kwargs
) -> list[LaunchDescriptionEntity]:
    ctx = SetupContext(context)

    arm_id = ctx.config("arm_id")
    tool_id = ctx.config("tool_id")
    rviz_config_path = ctx.config_path("rviz_config_path")

    use_rviz_bool = ctx.config_bool("use_rviz")
    use_gazebo_bool = ctx.config_bool("use_gazebo")
    use_aux_bool = ctx.config_bool("use_aux")
    on_aux_bool = ctx.config_bool("on_aux")
    robot_name_str = ctx.config("robot_name")
    gripper_eth = ctx.config("gripper_eth")

    if on_aux_bool and use_aux_bool:
        raise RuntimeError(
            "Cannot use both use_aux and on_aux at the same time.")

    external_controllers_names = ctx.config("external_controllers_names")
    external_controllers_params = ctx.config_path("external_controllers_params")

    logger = launch.logging.get_logger(__name__)

    if on_aux_bool:
        logger.info(f'LAUNCH: AUX')
    elif use_aux_bool:
        logger.info(f'LAUNCH: USE AUX')
    else:
        logger.info(f'LAUNCH: FULL')

    logger.info(f'GAZEBO: {use_gazebo_bool}')
    logger.info(f'ROBOT NAME: {robot_name_str}')
    logger.info(f'EXTERNAL CONTROLLERS: {external_controllers_names}')

    launch_config: list[LaunchDescriptionEntity] = []

    if not use_aux_bool:  # full launch or aux launch
        # gazebo or hardware launch
        if use_gazebo_bool:
            launch_config += [include_path_join("launch", "kuka",
                                                "kuka_simulation.launch.py")]

        else:
            launch_config += [include_path_join("launch", "kuka",
                                                "kuka_hardware.launch.py")]

        # switch to external controllers if any
        if external_controllers_names != "":
            external_controllers_names_list = ast.literal_eval(
                external_controllers_names)

            spawn_external_controllers = generate_controllers_spawner_launch_description(
                deepcopy(external_controllers_names_list),
                controller_params_files=(
                    [external_controllers_params]
                    if external_controllers_params != ""
                    else None
                ),

                extra_spawner_args=[
                    "--inactive",
                    "--controller-manager-timeout",
                    "10000000",
                    "--ros-args",
                    "-r", f"__ns:=/{robot_name_str}",
                ],
            )

            activate_external_controllers = ExecuteProcess(
                cmd=[
                        "ros2",
                        "control",
                        "switch_controllers",
                        "--controller-manager",
                        f"/{robot_name_str}/controller_manager",
                        "--activate",
                    ]
                    + deepcopy(external_controllers_names_list),
                output="screen",
            )

            activate_external_controllers_on_exit_event = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=spawn_external_controllers.entities[2],
                    on_exit=[activate_external_controllers],
                )
            )

            launch_config += [
                spawn_external_controllers,
                activate_external_controllers_on_exit_event
            ]

    if not on_aux_bool:  # full launch or using aux launch
        system_config_file = ctx.config_path("system_config_path")
        joint_limits_file = ctx.config_path("joint_limits_config_path")
        initial_joint_positions_file = ctx.config_path(
            "initial_joint_positions_path")

        xacro_args = {
            "robot_name": robot_name_str,
            "mode": "gazebo" if use_gazebo_bool else "hardware",
            "system_config_path": system_config_file,
            "joint_limits_path": joint_limits_file,
            "initial_joint_positions_path": initial_joint_positions_file,
        }

        if external_controllers_params != "":
            xacro_args["controller_params_path"] = external_controllers_params

        robot_description_file_substitution = path_join(
            "urdf", f"{arm_id}{'' if tool_id == '' else '_'}{tool_id}.xacro",
            pkg="agimus_description")

        robot_description = parameter_value_xacro(
            robot_description_file_substitution, xacro_args)

        xacro_collision_args = xacro_args.copy()
        xacro_collision_args["gazebo"] = "false"
        xacro_collision_args["with_sc"] = "true"

        robot_description_with_collision = parameter_value_xacro(
            robot_description_file_substitution, xacro_collision_args)

        # Separate publisher for a single hand in its namespace
        # (global urdf can be more complicated, with more hands, etd);
        # LFC has hardcoded the use of robot_state_publisher, then we remap
        # inputs and outputs as they are not wanted
        robot_urdf_publisher_node = Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[get_use_sim_time(),
                        {"robot_description": robot_description}],
            remappings=[*remap_to_ns(robot_name_str, 'tf', 'tf_static'),
                        ("joint_states", "unused_joint_states")],
            output="screen",
            namespace=robot_name_str,
        )

        joint_state_publisher_node = Node(
            package="joint_state_publisher",
            executable="joint_state_publisher",
            parameters=[
                get_use_sim_time(),
                {
                    "source_list": [
                        f"{robot_name_str}/joint_states",
                        # f"{arm_id_str}_gripper/joint_states",
                    ],
                    "rate": 30,
                },
            ],
        )

        robot_state_publisher_node = Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[get_use_sim_time(),
                        {"robot_description": robot_description}],
            output="screen",
        )

        robot_collision_publisher_node = Node(
            package="agimus_demos_common",
            executable="string_publisher",
            name="robot_description_with_collision_publisher",
            output="screen",
            parameters=[
                get_use_sim_time(),
                {
                    "topic_name": "robot_description_with_collision",
                    "string_value": robot_description_with_collision,
                },
            ],
            namespace=robot_name_str,
        )

        srdf_file_substitution = path_join(
            "config", f"{arm_id}.srdf", pkg=f"{arm_id}_moveit_config")
        srdf_file = srdf_file_substitution.perform(context)
        with open(srdf_file, "r") as f:
            robot_srdf_description = f.read()

        robot_srdf_publisher_node = Node(
            package="agimus_demos_common",
            executable="string_publisher",
            name="robot_srdf_description_publisher",
            output="screen",
            parameters=[
                {
                    "topic_name": "robot_srdf_description",
                    "string_value": robot_srdf_description,
                }
            ],
        )

        launch_config += [
            robot_urdf_publisher_node,
            joint_state_publisher_node,
            robot_state_publisher_node,
            robot_collision_publisher_node,
            robot_srdf_publisher_node,
        ]

        if use_rviz_bool:
            launch_config += [
                Node(
                    package="rviz2",
                    executable="rviz2",
                    parameters=[get_use_sim_time()],
                    arguments=["--display-config", rviz_config_path])
            ]

        if gripper_eth != "":
            launch_config += [
                *required_node(
                    quido_node(eth=gripper_eth,
                               namespace=robot_name_str)),
                * required_node(schunk_gripper_node(namespace=robot_name_str)),
            ]

    return launch_config


def generate_launch_description():
    return LaunchDescription(
        generate_default_kuka_args()
        + [OpaqueFunction(function=launch_setup)]
    )
