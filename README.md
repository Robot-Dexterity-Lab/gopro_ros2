# gopro_ros2

Stream GoPro video as ROS2 `CompressedImage` via USB capture card.

## Hardware

- GoPro (Hero 9+) with [GoPro Labs firmware](https://gopro.com/en/us/info/gopro-labs) — scan QR code in `asset/` for clean HDMI output
- [Elgato HD60 X](https://www.amazon.com/dp/B09V1KJ3J4) capture card (USB 3.0)

## Docker (recommended)

```bash
git clone https://github.com/Robot-Dexterity-Lab/gopro_ros2.git
cd gopro_ros2

# Humble (default)
docker build -t gopro_ros2:humble .

# Jazzy
docker build --build-arg ROS_DISTRO=jazzy -t gopro_ros2:jazzy .

# Run
docker run --rm --privileged --network=host -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix -v /dev:/dev \
  gopro_ros2:humble bash -c "source /ros2_ws/install/setup.bash && ros2 run gopro_ros2 gopro_stream"
```

Also works with VS Code Dev Containers — just open the repo and reopen in container.

## Native Install

```bash
cd ~/colcon_ws/src
git clone https://github.com/Robot-Dexterity-Lab/gopro_ros2.git
pip install opencv-python numpy
cd ~/colcon_ws && colcon build --packages-select gopro_ros2
source install/setup.bash
```

## Usage

```bash
ros2 run gopro_ros2 gopro_stream
```

Publishes to `/gopro/image_raw/compressed` at 1080p60.
