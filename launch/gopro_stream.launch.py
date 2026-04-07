"""Launch GoPro streamer node with default parameters."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("camera_idx", default_value="0"),
        DeclareLaunchArgument("dev_path", default_value=""),
        DeclareLaunchArgument("image_topic", default_value="/gopro/image_raw"),
        DeclareLaunchArgument("frame_id", default_value="gopro_camera"),
        DeclareLaunchArgument("width", default_value="1920"),
        DeclareLaunchArgument("height", default_value="1080"),
        DeclareLaunchArgument("fps", default_value="60"),
        DeclareLaunchArgument("no_gui", default_value="false"),

        Node(
            package="gopro_ros2",
            executable="gopro_stream",
            name="gopro_streamer",
            output="screen",
            parameters=[{
                "camera_idx": LaunchConfiguration("camera_idx"),
                "dev_path": LaunchConfiguration("dev_path"),
                "image_topic": LaunchConfiguration("image_topic"),
                "frame_id": LaunchConfiguration("frame_id"),
                "width": LaunchConfiguration("width"),
                "height": LaunchConfiguration("height"),
                "fps": LaunchConfiguration("fps"),
                "no_gui": LaunchConfiguration("no_gui"),
            }],
        ),
    ])
