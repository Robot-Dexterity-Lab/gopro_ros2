from setuptools import setup, find_packages
import os
from glob import glob

package_name = "gopro_ros2"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.json")),
        (os.path.join("share", package_name, "asset"), glob("asset/*")),
    ],
    install_requires=[
        "setuptools",
        "opencv-python",
        "numpy",
        "h5py",
        "pandas",
        "scipy",
        "tqdm",
    ],
    zip_safe=True,
    author="Jinzhou Li",
    author_email="jinzhou.li@duke.edu",
    description="GoPro ROS2 streaming and data collection",
    license="MIT",
    entry_points={
        "console_scripts": [
            "gopro_stream = gopro_ros2.streamer_node:main",
            "data_collect = gopro_ros2.collector_node:main",
            "tcp_transform = gopro_ros2.tcp_transform:main",
        ],
    },
)
