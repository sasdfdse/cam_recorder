from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='cam_recorder',
            executable='cam_recorder',
            name='cam_recorder',
            output='screen',
        ),
    ])
