import os
from typing import Optional
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, \
    Command, FindExecutable, PythonExpression
from launch.substitution import Substitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue
from launch.actions import RegisterEventHandler, EmitEvent
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.event_handlers import OnProcessExit
from launch import LaunchDescriptionEntity, LaunchContext
from agimus_demos_common.log_error import LogError


def path_join(*items: str | Substitution,
              pkg: str = "agimus_demos_common") -> Substitution:
    """Join items into a path to a package share."""
    return PathJoinSubstitution(
        [FindPackageShare(pkg), *items])


class SetupContext:
    def __init__(self, context: LaunchContext,
                 pkg: str = "agimus_demos_common"):
        self.context = context
        self.pkg = pkg

    def config(self, name: str) -> str:
        return LaunchConfiguration(name).perform(self.context)

    def config_bool(self, name: str) -> bool:
        return LaunchConfiguration(name).perform(self.context).lower() == "true"

    def config_path(self, *items: str, pkg: Optional[str] = None,
                    allow_empty: bool = False,
                    check: Optional[str] = 'file',
                    ) -> Optional[Substitution]:
        """Create a path to a package share.

        The package name can be given as a keyword argument 'pkg', it
        defaults to this package.

        The last item of *items (can be the only one) is the name of the launch
        argument that is resolved. If there is a single item only, it is split
        to optional package name (overrides the 'pkg') and a list of path items
        given as 'pkg:path/to/file' or 'path/to/file'.

        The list of items is then joined with the package share path.

        When allow_empty is True and the last item (after resolving) is empty,
        None is returned.
        """

        if pkg is None:
            pkg = self.pkg

        items = list(items)  # copy to avoid modifying the original list
        name = items[-1]
        items[-1] = LaunchConfiguration(name).perform(self.context)

        if items[-1] == "":
            if allow_empty:
                return None
            else:
                raise RuntimeError(f"Empty value of LaunchConfiguration {name}")

        if len(items) == 1:
            # try to split the item into an optional package name and a path
            if ":" in items[0]:
                pkg, items[0] = items[0].split(":", 1)

            items = items[0].split("/")

        pth_subst = path_join(*items, pkg=pkg)
        if check == 'file':
            pth = pth_subst.perform(self.context)
            # check for file existence
            if not os.path.isfile(pth):
                raise RuntimeError(f"LaunchConfiguration '{name}': path does " +
                                   f"not exist ({pth})")

        return pth_subst


def generate_default_kuka_args() -> list[DeclareLaunchArgument]:
    """Generates a list of default arguments for launch files used by
     Agimus Demos for Kuka robots.

    Returns:
        list[DeclareLaunchArgument]: List of DeclareLaunchArgument objects with
            arguments expected by `kuka_common.launch.py` and `kuka_common_lfc.launch.py`
    """

    return [
        DeclareLaunchArgument(
            "arm_id",
            default_value="iiwa7",
            description="ID of the type of arm used. Supported values: iiwa7",
            choices=["iiwa7"],
        ),

        DeclareLaunchArgument(
            "tool_id",
            default_value="",
            description="ID of the tool mounted on the arm",
        ),

        DeclareLaunchArgument(
            "robot_name",
            default_value="lbr",
            description="Name of the robot to distinguish multiple arms",
        ),
        DeclareLaunchArgument(
            "use_aux",
            default_value="false",
            description="Use another launch for LFC and robot control only.",
            choices=["true", "false"],
        ),
        DeclareLaunchArgument(
            "on_aux",
            default_value="false",
            description="This is the launch for LFC and robot control only.",
            choices=["true", "false"],
        ),
        DeclareLaunchArgument(
            "use_gazebo",
            default_value="false",
            description="Configures launch file for Gazebo simulation. ",
            choices=["true", "false"],
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value="false",
            description="Visualize the robot in RViz",
            choices=["true", "false"],
        ),
        DeclareLaunchArgument(
            "rviz_config_path",
            default_value=path_join(
                "rviz", "kuka",
                PythonExpression(
                    ['"', LaunchConfiguration("robot_name"),
                     '_preview.rviz"'])),
            description="Path to RViz configuration file",
        ),
        DeclareLaunchArgument(
            "joint_limits_config_path",
            default_value=PathJoinSubstitution(
                [
                    FindPackageShare("agimus_demos_common"),
                    "config",
                    "kuka",
                    "joint_limits.yaml",
                ]
            ),
            description="Path to joint limits YAML file",
        ),
        DeclareLaunchArgument(
            "initial_joint_positions_path",
            default_value=path_join(
                "config", "kuka", "initial_joint_positions.yaml"),
            description="Path to joint limits YAML file",
        ),
        DeclareLaunchArgument(
            "system_config_path",
            default_value=PathJoinSubstitution(
                [
                    FindPackageShare("agimus_demos_common"),
                    "config",
                    "kuka",
                    PythonExpression(
                        ['"', LaunchConfiguration("robot_name"),
                         '_system_config.yaml"']),
                ]
            ),
            description="Path to LBR system config YAML file",
        ),
        DeclareLaunchArgument(
            "gz_verbose",
            default_value="false",
            description="Whether to set verbosity level of Gazebo to 3.",
            choices=["true", "false"],
        ),
        DeclareLaunchArgument(
            "gz_headless",
            default_value="false",
            description="Whether to launch Gazebo in headless mode "
                        + "(no GUI is launched, only physics server).",
            choices=["true", "false"],
        ),
        DeclareLaunchArgument(
            "kuka_controllers_params",
            default_value=PathJoinSubstitution(
                [
                    FindPackageShare("agimus_demos_common"),
                    "config",
                    "kuka",
                    "controllers.yaml",
                ]
            ),
            description="Path to the yaml file use to define controller parameters.",
        ),
    ]


def generate_mpc_args():
    return [
        DeclareLaunchArgument(
            "use_mpc_debugger",
            default_value="false",
            description="Launches the mpc_debugger_node along.",
            choices=["false", "markers", "full"],
        ),
        DeclareLaunchArgument(
            "ocp_definition_file",
            default_value="ocp_definition_file.yaml",
            description="OCP configuration YAML file.",
        ),
        DeclareLaunchArgument(
            "controller_config_file",
            default_value="agimus_controller_params.yaml",
            description="Agimus controller configuration YAML file.",
        ),
        DeclareLaunchArgument(
            "obstacles_config_file",
            default_value="obstacles_none.xacro",
            description="Obstacles definition XACRO file.",
        ),
    ]


def get_use_sim_time() -> dict[str, LaunchConfiguration]:
    """Helper function creating action setting param `use_sim_time`.

    Returns:
        dict[str, LaunchConfiguration]: Dict mapping value of
        `use_gazebo` launch argument to `use_sim_time` param.
    """
    return {"use_sim_time": LaunchConfiguration("use_gazebo")}


def parameter_value_xacro(
        xacro_file_substitution: Substitution,
        xacro_args: dict | None = None) -> ParameterValue:
    """Apply xacro command to a xacro file with arguments."""

    if xacro_args is not None:
        params = [arg
                  for key, val in xacro_args.items()
                  for arg in (f" {key}:=", val)]
    else:
        params = []

    return ParameterValue(
        Command(
            [
                PathJoinSubstitution([FindExecutable(name="xacro")]),
                " ",
                xacro_file_substitution,
                # Convert dict to list of parameters
                *params,
            ]
        ),
        value_type=str,
    )


def include_path_join(*items: str, pkg: str = "agimus_demos_common",
                      launch_arguments=None) -> IncludeLaunchDescription:
    """Join items into a path to a package share and include as launch description ."""

    if launch_arguments is None:
        launch_arguments = []

    if isinstance(launch_arguments, dict):
        launch_arguments = [launch_arguments]

    args = {}
    # go through arguments, latter overwrites former
    for arg in launch_arguments:
        if isinstance(arg, dict):
            for k in arg:
                args[k] = arg[k]
        elif isinstance(arg, tuple):
            args[arg[0]] = arg[1]
        elif isinstance(arg, DeclareLaunchArgument):
            args[arg.name] = LaunchConfiguration(arg.name)
        else:
            raise RuntimeError(f"Unhandled lauch argument {arg}")

    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource([path_join(*items, pkg=pkg)]),
        launch_arguments=args.items())


class WaitForNonZeroJointsNode(Node):
    def __init__(self, robot_name_str):
        super().__init__(
            package="agimus_demos_common",
            executable="wait_for_non_zero_joints_node",
            parameters=[get_use_sim_time(), {'timeout': 10.0}],
            output="screen",
            namespace=robot_name_str,
            remappings=[("/joint_states", f"/{robot_name_str}/joint_states")],
        )


def wait_for_non_zero_joints_run(robot_name_str: str,
                                 run: list[LaunchDescriptionEntity]):
    wait_for_non_zero_joints_node = WaitForNonZeroJointsNode(robot_name_str)
    handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=wait_for_non_zero_joints_node,
            on_exit=run
        )
    )
    return wait_for_non_zero_joints_node, handler


def remap_to_ns(ns, *items: str):
    return [(f"/{item}", f"/{ns}/{item}") for item in items]


def required_node(node: Node) -> tuple[Node, RegisterEventHandler]:
    """Helper function to register an event handler to log an error if a
     required node exits.
     :returns: A tuple of the original node and the event handler.
     """
    handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=node,
            on_exit=[
                LogError(
                    msg=f"Required node exited: {node.node_package}/{node.node_executable}"),
                EmitEvent(event=Shutdown())]))

    return node, handler
